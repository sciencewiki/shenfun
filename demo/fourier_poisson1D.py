r"""
Solve Poisson equation on (0, 2pi) with periodic bcs

    \nabla^2 u = f, u(2pi) = u(0)

Use Fourier basis and find u in V such that

    (v, div(grad(u))) = (v, f)    for all v in V

V is the Fourier basis span{exp(1jkx)}_{k=-N/2}^{N/2-1}

"""
from sympy import Symbol, cos, sin, exp
import numpy as np
import matplotlib.pyplot as plt
from shenfun.fourier.bases import FourierBasis
from shenfun.inner import inner
from shenfun.operators import div, grad
from shenfun.arguments import TestFunction, TrialFunction

# Use sympy to compute a rhs, given an analytical solution
x = Symbol("x")
ue = cos(4*x)
fe = ue.diff(x, 2)

# Size of discretization
N = 32

ST = FourierBasis(N, np.float, plan=True)
u = TrialFunction(ST)
v = TestFunction(ST)

points = ST.points_and_weights(N)[0]

# Get f on quad points and exact solution
fj = np.array([fe.subs(x, j) for j in points], dtype=np.float)
uj = np.array([ue.subs(x, i) for i in points], dtype=np.float)

# Compute right hand side
f_hat = inner(v, fj)

# Solve Poisson equation
A = inner(v, div(grad(u)))
f_hat = A.solve(f_hat)

uq = ST.backward(f_hat)

assert np.allclose(uj, uq)

plt.figure()
plt.plot(points, uj)
plt.title("U")
plt.figure()
plt.plot(points, uq - uj)
plt.title("Error")
#plt.show()

SP = FourierBasis(N, np.float, plan=True, padding_factor=1.5)
up = SP.backward(f_hat)
