import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Polygon
from numba import njit
import time


@njit(cache=True)
def polar_decomposition(F):
    a, b = F[0,0], F[0,1]
    c, d = F[1,0], F[1,1]

    x = a + d
    y = c - b
    norm = np.sqrt(x*x + y*y)
    if norm < 1e-8:
        return np.eye(2)

    R = np.array([[ x, -y],
                  [ y,  x]]) / norm
    return R

@njit(cache=True)
def _compute_element_forces_numba(p0, p1, p2, x_inv, volume, young_modulus, poisson_ratio, use_cauchy):
    """Return 3x2 element force matrix for a single triangle."""
    forces = np.zeros((3, 2), dtype=np.float64)
    if volume == 0.0:
        return forces

    col0x = p1[0] - p0[0]
    col0y = p1[1] - p0[1]
    col1x = p2[0] - p0[0]
    col1y = p2[1] - p0[1]


    F = np.empty((2,2), dtype=np.float64)

    F[0,0] = col0x * x_inv[0, 0] + col1x * x_inv[1, 0]
    F[0,1] = col0x * x_inv[0, 1] + col1x * x_inv[1, 1]
    F[1,0] = col0y * x_inv[0, 0] + col1y * x_inv[1, 0]
    F[1,1] = col0y * x_inv[0, 1] + col1y * x_inv[1, 1]

    R = polar_decomposition(F)
    F_hat = R.T @ F
    grad_u_hat = F_hat - np.identity(2)

    coeff = young_modulus / (1.0 - poisson_ratio * poisson_ratio)
    shear_coeff = coeff * (1.0 - poisson_ratio) * 0.5


    strain00 = grad_u_hat[0,0]
    strain11 = grad_u_hat[1,1]
    strain01 = 0.5 * (grad_u_hat[0,1] + grad_u_hat[1,0])

    s0 = coeff * strain00 + coeff * poisson_ratio * strain11
    s1 = coeff * poisson_ratio * strain00 + coeff * strain11
    s2 = shear_coeff * strain01

    grad1x = x_inv[0, 0]
    grad1y = x_inv[0, 1]
    grad2x = x_inv[1, 0]
    grad2y = x_inv[1, 1]
    grad0x = -(grad1x + grad2x)
    grad0y = -(grad1y + grad2y)

    grads = (
        (grad0x, grad0y),
        (grad1x, grad1y),
        (grad2x, grad2y),
    )

    for idx in range(3):
        gradx, grady = grads[idx]
        fx = -(volume) * (s0 * gradx + s2 * grady)
        fy = -(volume) * (s2 * gradx + s1 * grady)
        Fx = R[0,0] * fx + R[0,1] * fy
        Fy = R[1,0] * fx + R[1,1] * fy
        forces[idx, 0] = Fx
        forces[idx, 1] = Fy

    return forces

@njit
def _compute_element_stiffness_numba(X_inv, volume, young_modulus, poisson_ratio):
    """
    Return 6x6 stiffness matrix for one triangle element.
    """
    # Plane stress elasticity matrix
    E, nu = young_modulus, poisson_ratio
    C = np.zeros((3,3))
    coeff = E / (1 - nu**2)
    C[0,0] = coeff
    C[0,1] = coeff * nu
    C[1,0] = coeff * nu
    C[1,1] = coeff
    C[2,2] = coeff * (1 - nu) / 2.0

    # Gradienty shape functions w referencyjnej przestrzeni
    dphi = X_inv.T
    grad0 = -dphi[:,0] - dphi[:,1]
    grad1 = dphi[:,0]
    grad2 = dphi[:,1]
    grads = [grad0, grad1, grad2]

    # B matrix (3x6)
    B = np.zeros((3,6))
    for i in range(3):
        gx, gy = grads[i]
        B[0, 2*i]   = gx
        B[1, 2*i+1] = gy
        B[2, 2*i]   = gy
        B[2, 2*i+1] = gx

    # Stiffness
    K_e = B.T @ C @ B * volume
    return K_e



@njit(cache=True)
def _assemble_forces_numba(
    positions,
    tri_indices,
    tri_x_inv,
    tri_volumes,
    masses,
    fixed_mask,
    gravity,
    young_modulus,
    poisson_ratio,
    use_cauchy,
    apply_constraints,
):
    """Compute the global force vector for the current configuration."""
    n = positions.shape[0]
    f_global = np.zeros((n, 2), dtype=np.float64)

    for i in range(n):
        f_global[i, 1] -= masses[i] * gravity

    tri_count = tri_indices.shape[0]
    for tri_idx in range(tri_count):
        volume = tri_volumes[tri_idx]
        if volume == 0.0:
            continue

        indices = tri_indices[tri_idx]
        i0 = indices[0]
        i1 = indices[1]
        i2 = indices[2]

        elem_forces = _compute_element_forces_numba(
            positions[i0],
            positions[i1],
            positions[i2],
            tri_x_inv[tri_idx],
            volume,
            young_modulus,
            poisson_ratio,
            use_cauchy,
        )

        f_global[i0, 0] += elem_forces[0, 0]
        f_global[i0, 1] += elem_forces[0, 1]
        f_global[i1, 0] += elem_forces[1, 0]
        f_global[i1, 1] += elem_forces[1, 1]
        f_global[i2, 0] += elem_forces[2, 0]
        f_global[i2, 1] += elem_forces[2, 1]

    if apply_constraints:
        for i in range(n):
            if fixed_mask[i]:
                f_global[i, 0] = 0.0
                f_global[i, 1] = 0.0

    return f_global



class FEMSoftBody:
    def __init__(self, young_modulus=100000, poisson_ratio=0.15, gravity=5,
                 fix_top=True, strain_type='cauchy'):
        self.E = young_modulus
        self.nu = poisson_ratio
        self.gravity = gravity
        self.fix_top = fix_top
        self.strain_type = strain_type == 'cauchy'  # 'cauchy' or 'green'

        self.particles = []
        self.triangles = []
        self.K_global = None
        self.K_eff = None
        self.positions = None
        self.positions0 = None
        self.velocities = None
        self.masses = None
        self.M = None
        self.fixed_mask = None
        self.tri_indices_array = None
        self.tri_x_inv_array = None
        self.tri_volume_array = None
        self.last_force_matrix = None
        self.time = 0.0

        self.create_mesh()
        self.precompute_rest_config()

    def create_mesh(self):
        """Create a square grid mesh of triangular elements."""
        grid_size = 8
        spacing = 0.2
        offset_x = 2.0
        offset_y = 1.0
        left_wall = 0.5
        right_wall = 5.5
        ground_y = 2.0

        self.particles = []
        for j in range(grid_size):
            for i in range(grid_size):
                x = (offset_x + i * spacing) / (spacing * grid_size)
                y = (offset_y + j * spacing) / (spacing * grid_size)
                pos = np.array([x, y], dtype=np.float64)
                self.particles.append({
                    'pos': pos.copy(),
                    'pos0': pos.copy(),
                    'vel': np.zeros(2, dtype=np.float64),
                    'mass': 1.0,
                    'fixed': (j == 0) and self.fix_top
                })

        self._initialize_particle_arrays()
        centroid = self.positions.mean(axis=0)
        self.positions -= centroid
        self.positions0 -= centroid
        self.positions[:, 1] *= -1
        self.positions0[:, 1] *= -1

        self.left_wall = left_wall - centroid[0]
        self.right_wall = right_wall - centroid[0]
        self.ground_y = -(ground_y - centroid[1])

        # Build triangle connectivity
        self.triangles = []
        for j in range(grid_size - 1):
            for i in range(grid_size - 1):
                idx = j * grid_size + i
                self.triangles.append({
                    'indices': [idx, idx + 1, idx + grid_size],
                    'X_inv': None,
                    'volume': 0,
                    'K_e': None
                })
                self.triangles.append({
                    'indices': [idx + 1, idx + grid_size + 1, idx + grid_size],
                    'X_inv': None,
                    'volume': 0,
                    'K_e': None
                })

    def precompute_rest_config(self):
        """Compute rest configuration matrices and areas."""
        x_inv_list = []
        volume_list = []
        for i, tri in enumerate(self.triangles):
            i0, i1, i2 = tri['indices']
            x0 = self.particles[i0]['pos0']
            x1 = self.particles[i1]['pos0']
            x2 = self.particles[i2]['pos0']

            X = np.column_stack([x1 - x0, x2 - x0])
            volume = 0.5 * abs(np.linalg.det(X))

            if volume < 1e-12:
                tri['X_inv'] = np.eye(2)
                tri['volume'] = 0
            else:
                tri['X_inv'] = np.linalg.inv(X)
                tri['volume'] = volume
            x_inv_list.append(tri['X_inv'])
            volume_list.append(tri['volume'])

            tri['K_e'] = _compute_element_stiffness_numba(tri['X_inv'], tri['volume'], self.E, self.nu)


        self.tri_indices_array = np.ascontiguousarray(
            np.array([tri['indices'] for tri in self.triangles], dtype=np.int64)
        )
        self.tri_x_inv_array = np.ascontiguousarray(np.array(x_inv_list, dtype=np.float64))
        self.tri_volume_array = np.ascontiguousarray(np.array(volume_list, dtype=np.float64))
        self.K_global = self.assemble_global_stiffness()

    def assemble_global_matrices(self, apply_constraints=True):
        """Assemble global force vector and stiffness matrix."""
        if self.tri_indices_array is None:
            return np.zeros((len(self.particles), 2), dtype=np.float64)

        f_global = _assemble_forces_numba(
            self.positions,
            self.tri_indices_array,
            self.tri_x_inv_array,
            self.tri_volume_array,
            self.masses,
            self.fixed_mask,
            self.gravity,
            self.E,
            self.nu,
            self.strain_type,
            False,
        )

        if self.time < 0.01:
            positions = self.positions
            center = np.mean(positions, axis=0)
            rotation_strength = 200.0
            for i in range(positions.shape[0]):
                r = positions[i] - center
                tangential = np.array([-r[1], r[0]])
                f_global[i] += rotation_strength * self.masses[i] * tangential

        k_contact = 1e5  # sztywność kontaktu
        damping = 50.0

        for i in range(self.positions.shape[0]):
            penetration = self.ground_y - self.positions[i,1]
            if penetration > 0:
                f_global[i,1] += k_contact * penetration
                f_global[i,1] -= damping * self.velocities[i,1]

        if apply_constraints:
            f_global[self.fixed_mask] = 0.0

        return f_global
    
    
    def assemble_global_stiffness(self):
        """
        Zwraca globalną macierz sztywności K (2n x 2n)
        """
        n = self.positions.shape[0]
        K_global = np.zeros((2*n, 2*n), dtype=np.float64)

        for tri in self.triangles:
            if tri['volume'] == 0.0:
                continue

            i0, i1, i2 = tri['indices']

            # Mapowanie lokalne -> globalne
            indices = [2*i0, 2*i0+1, 2*i1, 2*i1+1, 2*i2, 2*i2+1]
            for a in range(6):
                for b in range(6):
                    K_global[indices[a], indices[b]] += tri['K_e'][a, b]

        # Zero dla węzłów fixed
        for i in range(n):
            if self.fixed_mask[i]:
                K_global[2*i:2*i+2,:] = 0.0
                K_global[:,2*i:2*i+2] = 0.0
                K_global[2*i, 2*i] = 1.0
                K_global[2*i+1, 2*i+1] = 1.0

        return K_global


    def update(self, dt, newton_iters=10, tol=1e-6):
        """
        Backward Euler + Newton-Raphson.

        - dt: krok czasowy
        - newton_iters: maksymalna liczba iteracji Newtona
        - tol: tolerancja dla residualu
        """
        self.time += dt
        collision_coeff = 0.0

        n = self.positions.shape[0]
        x = self.positions.flatten()          # aktualne przybliżenie pozycji
        v = self.velocities.flatten()         # aktualne przybliżenie prędkości
        x_n = self.positions.flatten()        # pozycje sprzed kroku
        v_n = self.velocities.flatten()       # prędkości sprzed kroku

        # Brak sił zewnętrznych na razie (np. grawitacja)
        f_ext = np.zeros_like(x)
        self.K_eff = self.M/dt - dt * self.K_global

        # Zero dla węzłów fixed w K_eff
        for i in range(n):
            if self.fixed_mask[i]:
                self.K_eff[2*i:2*i+2, :] = 0.0
                self.K_eff[:, 2*i:2*i+2] = 0.0
                self.K_eff[2*i, 2*i] = 1.0
                self.K_eff[2*i+1, 2*i+1] = 1.0


        for iter_nr in range(newton_iters):
            # 1️⃣ Siły wewnętrzne w aktualnym przybliżeniu x
            f_int = self.assemble_global_matrices(apply_constraints=True).flatten()
            R = self.M @ ((x - x_n)/dt - v_n) - dt * f_int - f_ext

            # Zero dla węzłów fixed
            for i in range(n):
                if self.fixed_mask[i]:
                    R[2*i:2*i+2] = 0.0

            # Zero dla węzłów fixed w K_eff
            for i in range(n):
                if self.fixed_mask[i]:
                    self.K_eff[2*i:2*i+2, :] = 0.0
                    self.K_eff[:, 2*i:2*i+2] = 0.0
                    self.K_eff[2*i, 2*i] = 1.0
                    self.K_eff[2*i+1, 2*i+1] = 1.0

            # 4️⃣ Krok Newtona: K_eff * dx = -R
            dx = np.linalg.solve(self.K_eff, -R)
            x += dx
            v = (x - x_n)/dt

            # 5️⃣ Check convergence
            if np.linalg.norm(R) < tol:
                break

        # 6️⃣ Commit: aktualizacja pozycji i prędkości
        self.positions[:] = x.reshape((-1, 2))
        self.velocities[:] = v.reshape((-1, 2))

        for i in range(n):
            if self.positions[i, 1] < self.ground_y:
                self.positions[i, 1] = self.ground_y
                if collision_coeff == 0.0:
                    self.velocities[i, 1] = 0.0
                else:
                    self.velocities[i, 1] *= -collision_coeff

        self.last_force_matrix = self.assemble_global_matrices(apply_constraints=True)


    def get_triangle_positions(self):
        return [np.array([self.particles[i]['pos'] for i in tri['indices']])
                for tri in self.triangles]

    def get_particle_positions(self):
        return np.array([p['pos'] for p in self.particles])

    def _initialize_particle_arrays(self):
        """Create contiguous arrays for particle data and keep dict views in sync."""
        positions = np.array([p['pos'] for p in self.particles], dtype=np.float64)
        rest_positions = np.array([p['pos0'] for p in self.particles], dtype=np.float64)
        velocities = np.array([p['vel'] for p in self.particles], dtype=np.float64)
        masses = np.array([p['mass'] for p in self.particles], dtype=np.float64)
        fixed_mask = np.array([p['fixed'] for p in self.particles], dtype=bool)

        self.positions = np.ascontiguousarray(positions)
        self.positions0 = np.ascontiguousarray(rest_positions)
        self.velocities = np.ascontiguousarray(velocities)
        self.masses = np.ascontiguousarray(masses)
        n = self.positions.shape[0]
        self.M = np.zeros((2*n, 2*n), dtype=np.float64)
        for i in range(n):
            self.M[2*i, 2*i] = self.masses[i]
            self.M[2*i+1, 2*i+1] = self.masses[i]
        self.fixed_mask = fixed_mask

        for idx, particle in enumerate(self.particles):
            particle['pos'] = self.positions[idx]
            particle['pos0'] = self.positions0[idx]
            particle['vel'] = self.velocities[idx]


def main():
    sim = FEMSoftBody(
        young_modulus= 30000,
        poisson_ratio=0.15,
        gravity= 5,
        fix_top=False,
        strain_type='cauchy',
    )

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_aspect('equal')
    initial_pos = sim.get_particle_positions()
    x_extent = np.max(np.abs(initial_pos[:, 0])) + 1.0
    y_extent = np.max(np.abs(initial_pos[:, 1])) + 1.0
    ax.set_xlim(-x_extent, x_extent)
    ax.set_ylim(-y_extent, y_extent)
    ax.axhline(y=sim.ground_y, color='k', lw=2)
    ax.set_title("2D FEM Soft Body Simulation")

    patches = []
    for _ in sim.triangles:
        patch = Polygon([[0, 0], [0, 0], [0, 0]], fc='lightblue', ec='blue', alpha=0.6)
        ax.add_patch(patch)
        patches.append(patch)

    pts, = ax.plot([], [], 'o', color='darkblue', ms=4)
    fixed_pts, = ax.plot([], [], 'o', color='red', ms=6)
    zero_forces = np.zeros_like(initial_pos)
    force_quiver = ax.quiver(initial_pos[:, 0], initial_pos[:, 1],
                             zero_forces[:, 0], zero_forces[:, 1],
                             color='orange', angles='xy', scale_units='xy',
                             scale=1.0, width=0.003, alpha=0.7)
    txt = ax.text(0.02, 0.95, '', transform=ax.transAxes)
    frame = [0]
    force_scale = 0.003

    def init():
        force_quiver.set_offsets(initial_pos)
        force_quiver.set_UVC(zero_forces[:, 0], zero_forces[:, 1])
        return patches + [pts, fixed_pts, force_quiver, txt]


    def animate(_):
        start = time.time()
        dt = 0.005
        substeps = 50
        sdt = dt / substeps
        for _ in range(substeps):
            sim.update(sdt)

        tri_pos = sim.get_triangle_positions()
        for patch, verts in zip(patches, tri_pos):
            patch.set_xy(verts)

        pos = sim.get_particle_positions()
        mask = np.array([p['fixed'] for p in sim.particles])
        pts.set_data(pos[~mask, 0], pos[~mask, 1])
        fixed_pts.set_data(pos[mask, 0], pos[mask, 1])
        forces = np.array(sim.last_force_matrix)
        scaled_forces = forces * force_scale
        force_quiver.set_offsets(pos)
        force_quiver.set_UVC(scaled_forces[:, 0], scaled_forces[:, 1])
        frame[0] += 1
        txt.set_text(f"Frame: {frame[0]}")
        end = time.time()
        print(end - start)
        return patches + [pts, fixed_pts, force_quiver, txt]

    anim = FuncAnimation(fig, animate, init_func=init, frames=500, interval=20, blit=True)
    plt.show()


if __name__ == "__main__":
    main()
