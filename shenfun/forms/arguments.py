from numbers import Number, Integral
from scipy.special import sph_harm
import numpy as np
import sympy as sp
from shenfun.optimization.cython import evaluate
from mpi4py_fft import DistArray

__all__ = ('Expr', 'BasisFunction', 'TestFunction', 'TrialFunction', 'Function',
           'Array', 'Basis')

# Define some special functions required for spherical harmonics
cot = lambda x: 1/np.tan(x)
Ynm = lambda n, m, x, y : sph_harm(m, n, y, x)

def Basis(N, family='Fourier', bc=None, dtype='d', quad=None, domain=None,
          scaled=None, padding_factor=1.0, dealias_direct=False,
          coordinates=None, **kw):
    """Return basis for one dimension

    Parameters
    ----------

    N : int
        Number of quadrature points
    family : str, optional
        Choose one of

        - ``Chebyshev`` or ``C``,
        - ``Legendre`` or ``L``,
        - ``Fourier`` or ``F``,
        - ``Laguerre`` or ``La``,
        - ``Hermite`` or ``H``

    bc : str or two-tuple, optional
        Choose one of

        - two-tuple (a, b) - Dirichlet boundary condition with
          :math:`v(-1)=a` and :math:`v(1)=b`. For solving Poisson equation.
        - Dirichlet - Homogeneous Dirichlet
        - Neumann - Homogeneous Neumann
        - Biharmonic - Homogeneous Dirichlet and Neumann at both ends
        - Polar - For basis specific to polar coordinates
    dtype : str or np.dtype, optional
        The datatype of physical space (input to forward transforms)
    quad : str, optional
        Type of quadrature

        * For family=Chebyshev:

          - GL - Chebyshev-Gauss-Lobatto
          - GC - Chebyshev-Gauss

        * For family=Legendre:

          - LG - Legendre-Gauss
          - GL - Legendre-Gauss-Lobatto
        * For family=Laguerre:

          - LG - Laguerre-Gauss
        * For family=Hermite:

          - HG - Hermite-Gauss
    domain : two-tuple of floats, optional
        The computational domain
    scaled : bool
        Whether to use scaled basis (only Legendre)
    padding_factor : float, optional
        For padding backward transform (for dealiasing, and
        only for Fourier)
    dealias_direct : bool, optional
        Use 2/3-rule dealiasing (only Fourier)
    coordinates: 2-tuple (coordinate, position vector), optional
        Map for curvilinear coordinatesystem.
        The new coordinate variable in the new coordinate system is the first item.
        Second item is a tuple for the Cartesian position vector as function of the
        new variable in the first tuple. Example::

            theta = sp.Symbols('x', real=True, positive=True)
            rv = (sp.cos(theta), sp.sin(theta))

        where theta and rv are the first and second items in the 2-tuple.

    Examples
    --------
    >>> from shenfun import Basis
    >>> F0 = Basis(16, 'F')
    >>> C1 = Basis(32, 'C', quad='GC')

    """
    par = {'padding_factor': padding_factor,
           'dealias_direct': dealias_direct,
           'dtype': dtype,
           'coordinates': coordinates}
    par.update(kw)
    if domain is not None:
        par['domain'] = domain
    if family.lower() in ('fourier', 'f'):
        from shenfun import fourier
        if np.dtype(dtype).char in 'FDG':
            B = fourier.bases.C2CBasis
        else:
            B = fourier.bases.R2CBasis
        del par['dtype']
        return B(N, **par)

    elif family.lower() in ('chebyshev', 'c'):
        from shenfun import chebyshev
        if quad is not None:
            assert quad in ('GC', 'GL')
            par['quad'] = quad

        if bc is None:
            B = chebyshev.bases.Basis

        elif isinstance(bc, tuple):
            assert len(bc) in (2, 4)
            par['bc'] = bc
            if len(bc) == 2:
                B = chebyshev.bases.ShenDirichletBasis
            else:
                B = chebyshev.bases.ShenBiharmonicBasis

        elif isinstance(bc, str):
            if bc.lower() == 'dirichlet':
                B = chebyshev.bases.ShenDirichletBasis
            elif bc.lower() == 'neumann':
                B = chebyshev.bases.ShenNeumannBasis
            elif bc.lower() == 'neumann2':
                B = chebyshev.bases.SecondNeumannBasis
            elif bc.lower() == 'biharmonic':
                B = chebyshev.bases.ShenBiharmonicBasis
            elif bc.lower() == 'upperdirichlet':
                B = chebyshev.bases.UpperDirichletBasis
            elif bc.lower() == 'bipolar':
                B = chebyshev.bases.ShenBiPolarBasis
            elif bc.lower() == 'dirichletneumann':
                B = chebyshev.bases.DirichletNeumannBasis

        else:
            raise NotImplementedError

        return B(N, **par)

    elif family.lower() in ('legendre', 'l'):
        from shenfun import legendre
        if quad is not None:
            assert quad in ('LG', 'GL')
            par['quad'] = quad

        if scaled is not None:
            assert isinstance(scaled, bool)
            par['scaled'] = scaled

        if bc is None:
            B = legendre.bases.Basis

        elif isinstance(bc, tuple):
            assert len(bc) in (2, 4)
            par['bc'] = bc
            if len(bc) == 2:
                B = legendre.bases.ShenDirichletBasis
            else:
                B = legendre.bases.ShenBiharmonicBasis

        elif isinstance(bc, str):
            if bc.lower() == 'dirichlet':
                B = legendre.bases.ShenDirichletBasis
            elif bc.lower() == 'neumann':
                B = legendre.bases.ShenNeumannBasis
            elif bc.lower() == 'biharmonic':
                B = legendre.bases.ShenBiharmonicBasis
            elif bc.lower() == 'upperdirichlet':
                B = legendre.bases.UpperDirichletBasis
            elif bc.lower() == 'bipolar':
                B = legendre.bases.ShenBiPolarBasis
            elif bc.lower() == 'bipolar0':
                B = legendre.bases.ShenBiPolar0Basis
            elif bc.lower() == 'dirichletneumann':
                B = legendre.bases.DirichletNeumannBasis
            elif bc.lower() == 'neumanndirichlet':
                B = legendre.bases.NeumannDirichletBasis

        return B(N, **par)

    elif family.lower() in ('laguerre', 'la'):
        from shenfun import laguerre
        if quad is not None:
            assert quad in ('LG', 'GR')
            par['quad'] = quad

        if bc is None:
            B = laguerre.bases.Basis

        elif isinstance(bc, tuple):
            assert len(bc) == 2
            par['bc'] = bc
            B = laguerre.bases.ShenDirichletBasis

        elif isinstance(bc, str):
            if bc.lower() == 'dirichlet':
                B = laguerre.bases.ShenDirichletBasis

        else:
            raise NotImplementedError

        return B(N, **par)

    elif family.lower() in ('hermite', 'h'):
        from shenfun import hermite
        if quad is not None:
            assert quad in ('HG',)
            par['quad'] = quad

        B = hermite.bases.Basis

        if isinstance(bc, tuple):
            assert len(bc) == 2
            par['bc'] = bc

        elif isinstance(bc, str):
            assert bc.lower() == 'dirichlet'

        else:
            assert bc is None

        return B(N, **par)

    elif family.lower() in ('jacobi', 'j'):
        from shenfun import jacobi
        if quad is not None:
            assert quad in ('JG',)
            par['quad'] = quad

        if bc is None:
            B = jacobi.bases.Basis

        elif isinstance(bc, tuple):
            assert len(bc) in (2, 4)
            par['bc'] = bc
            if len(bc) == 2:
                B = jacobi.bases.ShenDirichletBasis
            else:
                assert np.all([abs(bci)<1e-12 for bci in bc])
                B = jacobi.bases.ShenBiharmonicBasis

        elif isinstance(bc, str):
            if bc.lower() == 'dirichlet':
                B = jacobi.bases.ShenDirichletBasis
            elif bc.lower() == 'biharmonic':
                B = jacobi.bases.ShenBiharmonicBasis
            elif bc.lower() == '6th order':
                B = jacobi.bases.ShenOrder6Basis
            else:
                raise NotImplementedError

        return B(N, **par)

    else:
        raise NotImplementedError


class Expr(object):
    r"""
    Class for spectral Galerkin forms

    An Expression that is linear in :class:`.TestFunction`,
    :class:`.TrialFunction` or :class:`.Function`. Exprs are used as input
    to :func:`.inner` or :func:`.project`.

    Parameters
    ----------
    basis : :class:`.BasisFunction`
        :class:`.TestFunction`, :class:`.TrialFunction` or :class:`.Function`
    terms : Numpy array of ndim = 3
        Describes operations performed in Expr

        - Index 0: Vector component. If Expr is rank = 0, then terms.shape[0] = 1.
          For vectors it equals ndim

        - Index 1: One for each term in the form. For example `div(grad(u))`
          has three terms in 3D:

        .. math::

           \partial^2u/\partial x^2 + \partial^2u/\partial y^2 + \partial^2u/\partial z^2

        - Index 2: The operations stored as an array of length = dim

        The Expr `div(grad(u))`, where u is a scalar, is as such represented
        as an array of shape (1, 3, 3), 1 meaning it's a scalar, the first 3
        because the Expr consists of the sum of three terms, and the last 3
        because it is 3D. The entire representation is::

           array([[[2, 0, 0],
                   [0, 2, 0],
                   [0, 0, 2]]])

        where the first [2, 0, 0] term has two derivatives in first direction
        and none in the others, the second [0, 2, 0] has two derivatives in
        second direction, etc.

    scales :  Numpy array of shape == terms.shape[:2]
        Representing a scalar multiply of each inner product. Note that
        the scalar can be a function of coordinates (using sympy).

    indices : Numpy array of shape == terms.shape[:2]
        Index into MixedTensorProductSpace. Only used when basis of form has
        rank > 0

    Examples
    --------
    >>> from shenfun import *
    >>> from mpi4py import MPI
    >>> comm = MPI.COMM_WORLD
    >>> C0 = Basis(16, 'F', dtype='D')
    >>> C1 = Basis(16, 'F', dtype='D')
    >>> R0 = Basis(16, 'F', dtype='d')
    >>> T = TensorProductSpace(comm, (C0, C1, R0))
    >>> v = TestFunction(T)
    >>> e = div(grad(v))
    >>> e.terms()
    array([[[2, 0, 0],
            [0, 2, 0],
            [0, 0, 2]]])
    >>> e2 = grad(v)
    >>> e2.terms()
    array([[[1, 0, 0]],
    <BLANKLINE>
           [[0, 1, 0]],
    <BLANKLINE>
           [[0, 0, 1]]])

    Note that `e2` in the example has shape (3, 1, 3). The first 3 because it
    is a vector, the 1 because each vector item contains one term, and the
    final 3 since it is a 3-dimensional tensor product space.
    """

    def __init__(self, basis, terms=None, scales=None, indices=None):
        self._basis = basis
        self._terms = terms
        self._scales = scales
        self._indices = indices
        ndim = self.function_space().dimensions
        if terms is None:
            self._terms = np.zeros((self.function_space().num_components(), 1, ndim),
                                   dtype=np.int)
        if scales is None:
            self._scales = np.ones((self.function_space().num_components(), 1), dtype=object)

        if indices is None:
            self._indices = basis.offset()+np.arange(self.function_space().num_components())[:, np.newaxis]

        assert np.prod(self._scales.shape) == self.num_terms()*self.num_components()

    def basis(self):
        """Return basis of Expr"""
        return self._basis

    @property
    def base(self):
        """Return base BasisFunction used in Expr"""
        return self._basis if self._basis.base is None else self._basis.base

    def function_space(self):
        """Return function space of basis in Expr"""
        return self._basis.function_space()

    def terms(self):
        """Return terms of Expr"""
        return self._terms

    def scales(self):
        """Return scales of Expr"""
        return self._scales

    @property
    def argument(self):
        """Return argument of Expr's basis"""
        return self._basis.argument

    def expr_rank(self):
        """Return rank of Expr"""
        if self.dimensions == 1:
            assert self._terms.shape[0] < 3
            return self._terms.shape[0]-1

        if self._terms.shape[0] == 1:
            return 0
        if self._terms.shape[0] == self._terms.shape[-1]:
            return 1
        if self._terms.shape[0] == self._terms.shape[-1]**2:
            return 2

    @property
    def rank(self):
        """Return rank of Expr's :class:`BasisFunction`"""
        return self._basis.rank

    def basis_rank(self):
        """Return rank of Expr's :class:`BasisFunction`"""
        return self._basis.rank

    def indices(self):
        """Return indices of Expr"""
        return self._indices

    def num_components(self):
        """Return number of components in Expr"""
        return self._terms.shape[0]

    def num_terms(self):
        """Return number of terms in Expr"""
        return self._terms.shape[1]

    @property
    def dimensions(self):
        """Return ndim of Expr"""
        return self._terms.shape[2]

    def index(self):
        if self.num_components() == 1:
            return self._basis.offset()
        return None

    def eval(self, x, output_array=None):
        """Return expression evaluated on x

        Parameters
        ----------
        x : float or array of floats
            Array must be of shape (D, N), for  N points in D dimensions

        """
        from shenfun import MixedTensorProductSpace
        from shenfun.fourier.bases import R2CBasis

        if len(x.shape) == 1: # 1D case
            x = x[None, :]

        V = self.function_space()
        basis = self.basis()

        if output_array is None:
            output_array = np.zeros(x.shape[1], dtype=V.forward.input_array.dtype)
        else:
            output_array[:] = 0

        work = np.zeros_like(output_array)

        assert V.dimensions == len(x)

        for vec, (base, ind) in enumerate(zip(self.terms(), self.indices())):
            for base_j, b0 in enumerate(base):
                M = []
                test_sp = V
                if isinstance(V, MixedTensorProductSpace):
                    test_sp = V.flatten()[ind[base_j]]
                r2c = -1
                last_conj_index = -1
                sl = -1
                for axis, k in enumerate(b0):
                    xx = test_sp[axis].map_reference_domain(np.squeeze(x[axis]))
                    P = test_sp[axis].evaluate_basis_derivative_all(xx, k=k)
                    if not test_sp[axis].domain_factor() == 1:
                        P *= test_sp[axis].domain_factor()**(k)
                    if len(x) > 1:
                        M.append(P[..., V.local_slice()[axis]])

                    if isinstance(test_sp[axis], R2CBasis) and len(x) > 1:
                        r2c = axis
                        m = test_sp[axis].N//2+1
                        if test_sp[axis].N % 2 == 0:
                            last_conj_index = m-1
                        else:
                            last_conj_index = m
                        sl = V.local_slice()[axis].start

                bv = basis if basis.rank == 0 else basis[ind[base_j]]
                work.fill(0)
                if len(x) == 1:
                    work = np.dot(P, bv)

                elif len(x) == 2:
                    work = evaluate.evaluate_2D(work, bv, M, r2c, last_conj_index, sl)

                elif len(x) == 3:
                    work = evaluate.evaluate_3D(work, bv, M, r2c, last_conj_index, sl)

                sc = self.scales()[vec, base_j]
                if not hasattr(sc, 'free_symbols'):
                    sc = float(sc)
                else:
                    sym0 = sc.free_symbols
                    m = []
                    for sym in sym0:
                        j = 'xyzrs'.index(str(sym))
                        m.append(x[j])
                    sc = sp.lambdify(sym0, sc)(*m)
                output_array += sc*work

        return output_array

    def __getitem__(self, i):
        basis = self._basis
        if basis.rank > 0:
            basis = self._basis[i]
        else:
            basis = self._basis
        if self.expr_rank() == 1:
            return Expr(basis,
                        self._terms[i][np.newaxis, :, :],
                        self._scales[i][np.newaxis, :],
                        self._indices[i][np.newaxis, :])

        elif self.expr_rank() == 2:
            ndim = self.dimensions
            return Expr(basis,
                        self._terms[i*ndim:(i+1)*ndim],
                        self._scales[i*ndim:(i+1)*ndim],
                        self._indices[i*ndim:(i+1)*ndim])
        else:
            raise NotImplementedError

    def __mul__(self, a):
        sc = self.scales().copy()
        if self.expr_rank() == 0:
            sc = sc * sp.sympify(a)

        else:
            if isinstance(a, tuple):
                assert len(a) == self.num_components()
                for i in range(self.num_components()):
                    sc[i] = sc[i] * sp.sympify(a[i])

            else:
                sc *= sp.sympify(a)

        return Expr(self._basis, self._terms.copy(), sc, self._indices.copy())

    def __rmul__(self, a):
        return self.__mul__(a)

    def __imul__(self, a):
        sc = self.scales()
        if self.expr_rank() == 0:
            sc *= sp.sympify(a)

        else:
            if isinstance(a, tuple):
                assert len(a) == self.dimensions
                for i in range(self.dimensions):
                    sc[i] = sc[i] * sp.sympify(a[i])

            else:
                sc *= sp.sympify(a)

        return self

    def __add__(self, a):
        assert isinstance(a, (Expr, BasisFunction))
        if not isinstance(a, Expr):
            a = Expr(a)
        assert self.num_components() == a.num_components()
        assert self.function_space() == a.function_space()
        assert self.argument == a.argument
        if id(self._basis) == id(a._basis):
            basis = self._basis
        else:
            assert id(self._basis.base) == id(a._basis.base)
            basis = self._basis.base
        return Expr(basis,
                    np.concatenate((self.terms(), a.terms()), axis=1),
                    np.concatenate((self.scales(), a.scales()), axis=1),
                    np.concatenate((self.indices(), a.indices()), axis=1))

    def __iadd__(self, a):
        assert isinstance(a, (Expr, BasisFunction))
        if not isinstance(a, Expr):
            a = Expr(a)
        assert self.num_components() == a.num_components()
        assert self.function_space() == a.function_space()
        assert self.argument == a.argument
        if id(self._basis) == id(a._basis):
            basis = self._basis
        else:
            assert id(self._basis.base) == id(a._basis.base)
            basis = self._basis.base
        self._basis = basis
        self._terms = np.concatenate((self.terms(), a.terms()), axis=1)
        self._scales = np.concatenate((self.scales(), a.scales()), axis=1)
        self._indices = np.concatenate((self.indices(), a.indices()), axis=1)
        return self

    def __sub__(self, a):
        assert isinstance(a, (Expr, BasisFunction))
        if not isinstance(a, Expr):
            a = Expr(a)
        assert self.num_components() == a.num_components()
        #assert self.function_space() == a.function_space()
        assert self.argument == a.argument
        if id(self._basis) == id(a._basis):
            basis = self._basis
        else:
            assert id(self._basis.base) == id(a._basis.base)
            basis = self._basis.base
        return Expr(basis,
                    np.concatenate((self.terms(), a.terms()), axis=1),
                    np.concatenate((self.scales(), -a.scales()), axis=1),
                    np.concatenate((self.indices(), a.indices()), axis=1))

    def __isub__(self, a):
        assert isinstance(a, (Expr, BasisFunction))
        if not isinstance(a, Expr):
            a = Expr(a)
        assert self.num_components() == a.num_components()
        assert self.function_space() == a.function_space()
        assert self.argument == a.argument
        if id(self._basis) == id(a._basis):
            basis = self._basis
        else:
            assert id(self._basis.base) == id(a._basis.base)
            basis = self._basis.base
        self._basis = basis
        self._terms = np.concatenate((self.terms(), a.terms()), axis=1)
        self._scales = np.concatenate((self.scales(), -a.scales()), axis=1)
        self._indices = np.concatenate((self.indices(), a.indices()), axis=1)
        return self

    def __neg__(self):
        return Expr(self.basis(), self.terms().copy(), -self.scales().copy(),
                    self.indices().copy())


class BasisFunction(object):
    """Base class for arguments to shenfun's Exprs

    Parameters
    ----------
    space : :class:`.TensorProductSpace`, :class:`.MixedTensorProductSpace` or
        :class:`.SpectralBase`
    index : int
        Local component of basis with rank > 0
    basespace : The base :class:`.MixedTensorProductSpace` if space is a
        subspace.
    offset : int
        The number of scalar spaces (i.e., :class:`.TensorProductSpace`es)
        ahead of this space
    base : The base :class:`BasisFunction`
    """

    def __init__(self, space, index=0, basespace=None, offset=0, base=None):
        self._space = space
        self._index = index
        self._basespace = basespace
        self._offset = offset
        self._base = base

    @property
    def rank(self):
        """Return rank of basis"""
        return self.function_space().rank

    def expr_rank(self):
        """Return rank of expression involving basis"""
        return Expr(self).expr_rank()

    def function_space(self):
        """Return function space of BasisFunction"""
        return self._space

    @property
    def basespace(self):
        """Return base space"""
        return self._basespace if self._basespace is not None else self._space

    @property
    def base(self):
        """Return base """
        return self._base if self._base is not None else self

    @property
    def argument(self):
        """Return argument of basis"""
        raise NotImplementedError

    def num_components(self):
        """Return number of components in basis"""
        return self.function_space().num_components()

    @property
    def dimensions(self):
        """Return dimensions of function space"""
        return self.function_space().dimensions

    def index(self):
        """Return index into base space"""
        return self._offset + self._index

    def offset(self):
        """Return offset of this basis

        The offset is the number of scalar :class:`.TensorProductSpace`es ahead
        of this space in a :class:`.MixedTensorProductSpace`.
        """
        return self._offset

    def __getitem__(self, i):
        #assert self.rank > 0
        basespace = self.basespace
        base = self.base
        space = self._space[i]
        offset = self._offset
        for k in range(i):
            offset += self._space[k].num_components()
        t0 = BasisFunction(space, i, basespace, offset, base)
        return t0

    def __mul__(self, a):
        b = Expr(self)
        return b*a

    def __rmul__(self, a):
        return self.__mul__(a)

    def __imul__(self, a):
        raise RuntimeError

    def __add__(self, a):
        assert isinstance(a, (Expr, BasisFunction))
        b = Expr(self)
        return b+a

    def __iadd__(self, a):
        raise RuntimeError

    def __sub__(self, a):
        assert isinstance(a, (Expr, BasisFunction))
        b = Expr(self)
        return b-a

    def __isub__(self, a):
        raise RuntimeError


class TestFunction(BasisFunction):
    """Test function - BasisFunction with argument = 0

    Parameters
    ----------
    space: :class:`TensorProductSpace` or :class:`MixedTensorProductSpace`
    index: int, optional
        Component of basis with rank > 0
    basespace : The base :class:`.MixedTensorProductSpace` if space is a
        subspace.
    offset : int
        The number of scalar spaces (i.e., :class:`.TensorProductSpace`es)
        ahead of this space
    base : The base :class:`TestFunction`
    """

    def __init__(self, space, index=0, basespace=None, offset=0, base=None):
        BasisFunction.__init__(self, space, index, basespace, offset, base)

    def __getitem__(self, i):
        #assert self.rank > 0
        basespace = self.basespace
        base = self.base
        space = self._space[i]
        offset = self._offset
        for k in range(i):
            offset += self._space[k].num_components()
        t0 = TestFunction(space, i, basespace, offset, base)
        return t0

    @property
    def argument(self):
        return 0

class TrialFunction(BasisFunction):
    """Trial function - BasisFunction with argument = 1

    Parameters
    ----------
    space: :class:`TensorProductSpace` or :class:`MixedTensorProductSpace`
    index: int, optional
        Component of basis with rank > 0
    basespace : The base :class:`.MixedTensorProductSpace` if space is a
        subspace.
    offset : int
        The number of scalar spaces (i.e., :class:`.TensorProductSpace`es)
        ahead of this space
    base : The base :class:`TrialFunction`
    """
    def __init__(self, space, index=0, basespace=None, offset=0, base=None):
        BasisFunction.__init__(self, space, index, basespace, offset, base)

    def __getitem__(self, i):
        #assert self.rank > 0
        basespace = self.basespace
        base = self.base
        space = self._space[i]
        offset = self._offset
        for k in range(i):
            offset += self._space[k].num_components()
        t0 = TrialFunction(space, i, basespace, offset, base)
        return t0

    @property
    def argument(self):
        return 1

class ShenfunBaseArray(DistArray):

    def __new__(cls, space, val=0, buffer=None):

        if hasattr(space, 'points_and_weights'): # 1D case
            if cls.__name__ == 'Function':
                dtype = space.forward.output_array.dtype
                shape = space.forward.output_array.shape
            elif cls.__name__ == 'Array':
                dtype = space.forward.input_array.dtype
                shape = space.forward.input_array.shape

            if not space.num_components() == 1:
                shape = (space.num_components(),) + shape

            if hasattr(buffer, 'free_symbols'):
                # Evaluate sympy function on entire mesh
                x = buffer.free_symbols.pop()
                buffer = sp.lambdify(x, buffer)
                buf = buffer(space.mesh()).astype(space.forward.input_array.dtype)
                buffer = Array(space)
                buffer[:] = buf
                if cls.__name__ == 'Function':
                    buf = Function(space)
                    buf = buffer.forward(buf)
                    buffer = buf

            obj = DistArray.__new__(cls, shape, buffer=buffer, dtype=dtype,
                                    rank=space.is_composite_space)
            obj._space = space
            obj._offset = 0
            if buffer is None and isinstance(val, Number):
                obj[:] = val
            return obj

        if cls.__name__ == 'Function':
            forward_output = True
            p0 = space.forward.output_pencil
            dtype = space.forward.output_array.dtype
        elif cls.__name__ == 'Array':
            forward_output = False
            p0 = space.backward.output_pencil
            dtype = space.forward.input_array.dtype

        # Evaluate sympy function on entire mesh
        if hasattr(buffer, 'free_symbols'):
            sym0 = buffer.free_symbols
            mesh = space.local_mesh(True)
            m = []
            for sym in sym0:
                j = 'xyzrs'.index(str(sym))
                m.append(mesh[j])

            buf = sp.lambdify(sym0, buffer, modules=['numpy', {'cot': cot, 'Ynm': Ynm}])(*m).astype(space.forward.input_array.dtype)
            buffer = Array(space)
            buffer[:] = buf
            if cls.__name__ == 'Function':
                buf = Function(space)
                buf = buffer.forward(buf)
                buffer = buf

        global_shape = space.global_shape(forward_output)
        obj = DistArray.__new__(cls, global_shape,
                                subcomm=p0.subcomm, val=val, dtype=dtype,
                                buffer=buffer, alignment=p0.axis,
                                rank=space.is_composite_space)
        obj._space = space
        obj._offset = 0
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return

        self._space = getattr(obj, '_space', None)
        self._rank = getattr(obj, '_rank', None)
        self._p0 = getattr(obj, '_p0', None)
        self._offset = getattr(obj, '_offset', None)

    def function_space(self):
        """Return function space of array ``self``"""
        return self._space

    def index(self):
        """Return index for scalar into mixed base space"""
        if self.base is None:
            return None

        #if self.base.shape == self.shape:
        #    return None

        #if self.rank > 0:
        #    return None

        if self.function_space().num_components() > 1:
            return None

        data_self = self.ctypes.data
        data_base = self.base.ctypes.data
        itemsize = self.itemsize
        return (data_self - data_base) // (itemsize*np.prod(self.shape))

    @property
    def argument(self):
        """Return argument of basis"""
        return 2

    @property
    def global_shape(self):
        """Return global shape of ``self``"""
        return self.function_space().global_shape(self.forward_output)

    @property
    def forward_output(self):
        """Return whether ``self`` is the result of a forward transform"""
        raise NotImplementedError

    def __getitem__(self, i):
        if self.ndim == 1:
            return np.ndarray.__getitem__(self, i)

        if self.rank > 0 and isinstance(i, Integral):
            # Return view into mixed Function
            space = self._space[i]
            offset = 0
            for j in range(i):
                offset += self._space[j].num_components()
            ns = space.num_components()
            s = slice(offset, offset+ns) if ns > 1 else offset
            v0 = np.ndarray.__getitem__(self, s)
            v0._space = space
            v0._offset = offset + self.offset()
            v0._rank = self.rank - (self.ndim - v0.ndim)
            #v0._rank = v0.ndim - self.dimensions
            return v0

        return np.ndarray.__getitem__(self.v, i)

    def dim(self):
        return self.function_space().dim()

    def dims(self):
        return self.function_space().dims()


class Function(ShenfunBaseArray, BasisFunction):
    r"""
    Spectral Galerkin function for given :class:`.TensorProductSpace` or :func:`.Basis`

    The Function is the product of all 1D basis expansions, that for each
    dimension is defined like

    .. math::

        u(x) = \sum_{k \in \mathcal{K}} \hat{u}_k \psi_k(x),

    where :math:`\psi_k(x)` are the trial functions and
    :math:`\{\hat{u}_k\}_{k\in\mathcal{K}}` are the expansion coefficients.
    Here an index set :math:`\mathcal{K}=0, 1, \ldots, N` is used
    to simplify notation.

    For an M+1-dimensional TensorProductSpace with coordinates
    :math:`x_0, x_1, \ldots, x_M` we get

    .. math::

        u(x_{0}, x_{1}, \ldots, x_{M}) = \sum_{k_0 \in \mathcal{K}_0}\sum_{k_1 \in \mathcal{K}_1} \ldots \sum_{k_M \in \mathcal{K}_M} \hat{u}_{k_0, k_1, \ldots k_M} \psi_{k_0}(x_0) \psi_{k_1}(x_1) \ldots \psi_{k_M}(x_M),

    where :math:`\mathcal{K}_j` is the index set for the wavenumber mesh
    along axis :math:`j`.

    Note that for a Cartesian mesh in 3D it would be natural to use coordinates
    :math:`(x, y, z) = (x_0, x_1, x_2)` and the expansion would be the
    simpler and somewhat more intuitive

    .. math::

        u(x, y, z) = \sum_{l \in \mathcal{K}_0}\sum_{m \in \mathcal{K}_1} \sum_{n \in \mathcal{K}_2} \hat{u}_{l, m, n} \psi_{l}(x) \psi_{m}(y) \psi_{n}(z).

    The Function's values (the Numpy array) represent the :math:`\hat{u}` array.
    The trial functions :math:`\psi` may differ in the different directions.
    They are chosen when creating the TensorProductSpace.

    Parameters
    ----------
    space : :class:`.TensorProductSpace`
    val : int or float
        Value used to initialize array
    buffer : Numpy array, :class:`.Function` or sympy `Expr`
        If array it must be of correct shape.
        A sympy expression is evaluated on the quadrature mesh and
        forward transformed to create the buffer array.


    .. note:: For more information, see `numpy.ndarray <https://docs.scipy.org/doc/numpy/reference/generated/numpy.ndarray.html>`_

    Examples
    --------
    >>> from mpi4py import MPI
    >>> from shenfun import Basis, TensorProductSpace, Function
    >>> K0 = Basis(8, 'F', dtype='D')
    >>> K1 = Basis(8, 'F', dtype='d')
    >>> T = TensorProductSpace(MPI.COMM_WORLD, [K0, K1])
    >>> u = Function(T)
    >>> K2 = Basis(8, 'C', bc=(0, 0))
    >>> T2 = TensorProductSpace(MPI.COMM_WORLD, [K0, K1, K2])
    >>> v = Function(T2)

    """
    # pylint: disable=too-few-public-methods,too-many-arguments

    def __init__(self, space, val=0, buffer=None):
        BasisFunction.__init__(self, space, offset=0)

    @property
    def forward_output(self):
        return True

    def eval(self, x, output_array=None):
        """Evaluate Function at points

        Parameters
        ----------
        points : float or array of floats
        coefficients : array
            Expansion coefficients
        output_array : array, optional
            Return array, function values at points

        Examples
        --------
        >>> import sympy as sp
        >>> K0 = Basis(9, 'F', dtype='D')
        >>> K1 = Basis(8, 'F', dtype='d')
        >>> T = TensorProductSpace(MPI.COMM_WORLD, [K0, K1], axes=(0, 1))
        >>> X = T.local_mesh()
        >>> x, y = sp.symbols("x,y")
        >>> ue = sp.sin(2*x) + sp.cos(3*y)
        >>> ul = sp.lambdify((x, y), ue, 'numpy')
        >>> ua = Array(T, buffer=ul(*X))
        >>> points = np.random.random((2, 4))
        >>> u = ua.forward()
        >>> u0 = u.eval(points).real
        >>> assert np.allclose(u0, ul(*points))
        """
        return self.function_space().eval(x, self, output_array)

    def backward(self, output_array=None, uniform=False):
        """Return Function evaluated on quadrature mesh"""
        space = self.function_space()
        if output_array is None:
            output_array = Array(space)
        if uniform is True:
            output_array = space.backward_uniform(self, output_array)
        else:
            output_array = space.backward(self, output_array)
        return output_array

    def to_ortho(self, output_array=None):
        """Project Function to orthogonal basis"""
        space = self.function_space()
        if output_array is None:
            output_array = Function(space)

        # In case of mixed space make a loop
        if space.rank > 0:
            spaces = space.flatten()
            # output_array will now loop over first index
        else:
            spaces = [space]
            output_array = [output_array]
            self = [self]

        for i, space in enumerate(spaces):
            if space.dimensions > 1:
                naxes = space.get_nonperiodic_axes()
                axis = naxes[0]
                base = space.bases[axis]
                if not base.is_orthogonal:
                    output_array[i] = base.to_ortho(self[i], output_array[i])
                if len(naxes) > 1:
                    input_array = np.zeros_like(output_array[i].__array__())
                    for axis in naxes[1:]:
                        base = space.bases[axis]
                        input_array[:] = output_array[i]
                        if not base.is_orthogonal:
                            output_array[i] = base.to_ortho(input_array, output_array[i])
            else:
                output_array[i] = space.to_ortho(self[i], output_array[i])
        if isinstance(output_array, list):
            return output_array[0]
        return output_array

    def mask_nyquist(self, mask=None):
        """Set self to have zeros in Nyquist coefficients"""
        self.function_space().mask_nyquist(self, mask=mask)

    def assign(self, u_hat):
        """Assign self to u_hat of possibly different size

        Parameters
        ----------
        u_hat : Function
            Function of possibly different shape than self. Must have
            the same function_space
        """
        from shenfun import VectorTensorProductSpace
        if self.ndim == 1:
            assert u_hat.__class__ == self.__class__
            if self.shape[0] < u_hat.shape[0]:
                self.function_space()._padding_backward(self, u_hat)
            elif self.shape[0] == u_hat.shape[0]:
                u_hat[:] = self
            elif self.shape[0] > u_hat.shape[0]:
                self.function_space()._truncation_forward(self, u_hat)
            return u_hat

        space = self.function_space()
        newspace = u_hat.function_space()

        if isinstance(space, VectorTensorProductSpace):
            for i, self_i in enumerate(self):
                u_hat[i] = self_i.assign(u_hat[i])
            return u_hat

        same_bases = True
        for base0, base1 in zip(space.bases, newspace.bases):
            if not base0.__class__ == base1.__class__:
                same_bases = False
                break
        assert same_bases, "Can only assign on spaces with the same underlying bases"

        N = []
        for newbase in newspace.bases:
            N.append(newbase.N)

        u_hat = self.refine(N, output_array=u_hat)
        return u_hat

    def refine(self, N, output_array=None):
        """Return self with new number of quadrature points

        Parameters
        ----------
        N : number or sequence of numbers
            The new number of quadrature points

        Note
        ----
        If N is smaller than for self, then a truncated array
        is returned. If N is greater than before, then the
        returned array is padded with zeros.

        """
        from shenfun.fourier.bases import R2CBasis
        from shenfun import VectorTensorProductSpace

        if self.ndim == 1:
            assert isinstance(N, Number)
            space = self.function_space()
            if output_array is None:
                refined_basis = space.get_refined(N)
                output_array = Function(refined_basis)
            output_array = self.assign(output_array)
            return output_array

        space = self.function_space()

        if isinstance(space, VectorTensorProductSpace):
            if output_array is None:
                output_array = [None]*len(self)
            for i, array in enumerate(self):
                output_array[i] = array.refine(N, output_array=output_array[i])
            if isinstance(output_array, list):
                T = output_array[0].function_space()
                VT = VectorTensorProductSpace(T)
                output_array = np.array(output_array)
                output_array = Function(VT, buffer=output_array)
            return output_array

        axes = [bx for ax in space.axes for bx in ax]
        base = space.bases[axes[0]]
        global_shape = list(self.global_shape) # Global shape in spectral space
        factor = N[axes[0]]/self.function_space().bases[axes[0]].N
        if isinstance(base, R2CBasis):
            global_shape[axes[0]] = int((2*global_shape[axes[0]]-2)*factor)//2+1
        else:
            global_shape[axes[0]] = int(global_shape[axes[0]]*factor)
        c1 = DistArray(global_shape,
                       subcomm=self.pencil.subcomm,
                       dtype=self.dtype,
                       alignment=self.alignment)
        if self.global_shape[axes[0]] <= global_shape[axes[0]]:
            base._padding_backward(self, c1)
        else:
            base._truncation_forward(self, c1)
        for ax in axes[1:]:
            c0 = c1.redistribute(ax)
            factor = N[ax]/self.function_space().bases[ax].N

            # Get a new padded array
            base = space.bases[ax]
            if isinstance(base, R2CBasis):
                global_shape[ax] = int(base.N*factor)//2+1
            else:
                global_shape[ax] = int(global_shape[ax]*factor)
            c1 = DistArray(global_shape,
                           subcomm=c0.pencil.subcomm,
                           dtype=c0.dtype,
                           alignment=ax)

            # Copy from c0 to d0
            if self.global_shape[ax] <= global_shape[ax]:
                base._padding_backward(c0, c1)
            else:
                base._truncation_forward(c0, c1)

        # Reverse transfer to get the same distribution as u_hat
        for ax in reversed(axes[:-1]):
            c1 = c1.redistribute(ax)

        if output_array is None:
            refined_space = space.get_refined(N)
            output_array = Function(refined_space, buffer=c1)
        else:
            output_array[:] = c1
        return output_array


class Array(ShenfunBaseArray):
    r"""
    Numpy array for :class:`.TensorProductSpace`

    The Array is the result of a :class:`.Function` evaluated on its quadrature
    mesh.

    The Function is the product of all 1D basis expansions, that for each
    dimension is defined like

    .. math::

        u(x) = \sum_{k \in \mathcal{K}} \hat{u}_k \psi_k(x),

    where :math:`\psi_k(x)` are the trial functions and
    :math:`\{\hat{u}_k\}_{k\in\mathcal{K}}` are the expansion coefficients.
    Here an index set :math:`\mathcal{K}=0, 1, \ldots, N` is used to
    simplify notation.

    For an M+1-dimensional TensorProductSpace with coordinates
    :math:`x_0, x_1, \ldots, x_M` we get

    .. math::

        u(x_{0}, x_{1}, \ldots, x_{M}) = \sum_{k_0 \in \mathcal{K}_0}\sum_{k_1 \in \mathcal{K}_1} \ldots \sum_{k_M \in \mathcal{K}_M} \hat{u}_{k_0, k_1, \ldots k_M} \psi_{k_0}(x_0) \psi_{k_1}(x_1) \ldots \psi_{k_M}(x_M),

    where :math:`\mathcal{K}_j` is the index set for the wavenumber mesh
    along axis :math:`j`.

    Note that for a Cartesian mesh in 3D it would be natural to use coordinates
    :math:`(x, y, z) = (x_0, x_1, x_2)` and the expansion would be the
    simpler and somewhat more intuitive

    .. math::

        u(x, y, z) = \sum_{l \in \mathcal{K}_0}\sum_{m \in \mathcal{K}_1} \sum_{n \in \mathcal{K}_2} \hat{u}_{l, m, n} \psi_{l}(x) \psi_{m}(y) \psi_{n}(z).

    The Array's values (the Numpy array) represent the left hand side,
    evaluated on the Cartesian quadrature mesh. With this we mean the
    :math:`u(x_i, y_j, z_k)` array, where :math:`\{x_i\}_{i=0}^{N_0}`,
    :math:`\{y_j\}_{j=0}^{N_1}` and :math:`\{z_k\}_{k=0}^{N_2}` represent
    the mesh along the three directions. The quadrature mesh is then

    .. math::

        (x_i, y_j, z_k) \quad \forall \, (i, j, k) \in [0, 1, \ldots, N_0] \times [0, 1, \ldots, N_1] \times [0, 1, \ldots, N_2]

    The entire spectral Galerkin function can be obtained using the
    :class:`.Function` class.

    Parameters
    ----------

    space : :class:`.TensorProductSpace` or :class:`.SpectralBase`
    val : int or float
        Value used to initialize array
    buffer : Numpy array, :class:`.Function` or sympy `Expr`
        If array it must be of correct shape.
        A sympy expression is evaluated on the quadrature mesh and
        the result is used as buffer.

    .. note:: For more information, see `numpy.ndarray <https://docs.scipy.org/doc/numpy/reference/generated/numpy.ndarray.html>`_

    Examples
    --------
    >>> from mpi4py import MPI
    >>> from shenfun import Basis, TensorProductSpace, Function
    >>> K0 = Basis(8, 'F', dtype='D')
    >>> K1 = Basis(8, 'F', dtype='d')
    >>> FFT = TensorProductSpace(MPI.COMM_WORLD, [K0, K1])
    >>> u = Array(FFT)
    """

    @property
    def forward_output(self):
        return False

    def forward(self, output_array=None):
        """Return Function used to evaluate Array"""
        space = self.function_space()
        if output_array is None:
            output_array = Function(space)
        output_array = space.forward(self, output_array)
        return output_array

    def offset(self):
        """Return offset of this basis

        The offset is the number of scalar :class:`.TensorProductSpace`es ahead
        of this Arrays space in a :class:`.MixedTensorProductSpace`.
        """
        return self._offset
