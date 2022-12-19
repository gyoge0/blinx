import jax.numpy as jnp
import jax
from promap.trace_model import TraceModel
from promap.fluorescence_model import FluorescenceModel
from promap import transition_matrix
import optax


def optimize_params(y, trace,
                    p_on_guess=0.1,
                    p_off_guess=0.1,
                    mu_guess=50.,
                    sigma_guess=0.2,
                    mu_b_guess=200,
                    mu_lr=5):
    '''
    Use gradient descent to fit kinetic (p_on / off) and emission
    (mu / sigma) parameters to an intensity trace, for a given value of y

    Args:
        y (int):
            - The maximum number of elements that can be on.

        trace (jnp array):
            - ordered array of intensity observations
            - shape (number_observations, )

        p_on_guess / p_off_guess (float):
            - value between 0 and 1 not inclusive

        mu_guess (float):
            - the mean intensity on a single fluorophore when on

        sigma_guess (float):
            - the variance of the intensity of a single fluorophore

    Returns:
        The maximum log-likelihood that the trace arrose from y elements,
        as well as the optimum values of p_on, p_off, mu, and sigma
    '''

    # create a new loss function for the given y value
    likelihood_grad_func = _create_likelihood_grad_func(y, mu_b_guess)

    params = (p_on_guess, p_off_guess, mu_guess, sigma_guess)
    optimizer = optax.adam(learning_rate=1e-3, mu_dtype='uint64')
    opt_state = optimizer.init(params)

    mu_optimizer = optax.sgd(learning_rate=mu_lr)
    mu_opt_state = mu_optimizer.init(params[2])

    old_likelihood = 1
    diff = 10
    p_on = p_on_guess
    p_off = p_off_guess
    mu = mu_guess
    sigma = sigma_guess

    while diff > 1e-4:

        likelihood, grads = likelihood_grad_func(p_on, p_off, mu, sigma,
                                                 trace, mu_b_guess)

        updates, opt_state = optimizer.update(grads, opt_state)

        mu_update, mu_opt_state = mu_optimizer.update(grads[2], mu_opt_state)

        p_on, p_off, _, sigma = optax.apply_updates((p_on, p_off, mu,
                                                      sigma), updates)
        mu = optax.apply_updates((mu), mu_update)

        diff = jnp.abs(likelihood - old_likelihood)
        old_likelihood = likelihood

        print(
            f'{likelihood:.2f}, {p_on:.4f}, {p_off:.4f}'
            f', {mu:.4f}, {sigma:.4f}')
        print('-'*50)

    return -1*likelihood, p_on, p_off, mu, sigma

def _likelihood_func(y, p_on, p_off, mu, sigma, trace, mu_b_guess=200):
    fluorescence_model = FluorescenceModel(
        mu_i=mu,
        sigma_i=sigma,
        mu_b=mu_b_guess,
        sigma_b=0.05)
    t_model = TraceModel(fluorescence_model)

    probs = t_model.fluorescence_model.p_x_given_zs(trace, y)

    comb_matrix = transition_matrix._create_comb_matrix(y)
    comb_matrix_slanted = transition_matrix._create_comb_matrix(
        y,
        slanted=True)

    def c_transition_matrix_2(p_on, p_off):
        return transition_matrix.create_transition_matrix(
            y, p_on, p_off,
            comb_matrix,
            comb_matrix_slanted)

    transition_mat = c_transition_matrix_2(p_on, p_off)
    p_initial = transition_matrix.p_initial(y, transition_mat)
    likelihood = t_model.get_likelihood(
        probs,
        transition_mat,
        p_initial)

    # need to flip to positive value for grad descent
    return -1 * likelihood

def _create_likelihood_grad_func(y, mu_b_guess=200):
    '''
    Helper function that creates a loss function used to fit parameters
    p_on, p_off, mu, and simga

    Args:
        y (int):
            - The maximum number of elements that can be on

    Returns:
        a jited function that returns the likelihood, which acts as a loss,
        when given values for p_on, p_off, mu, and sigma
    '''

    def likelihood_func(p_on, p_off, mu, sigma, trace, mu_b_guess=200):
        fluorescence_model = FluorescenceModel(
            mu_i=mu,
            sigma_i=sigma,
            mu_b=mu_b_guess,
            sigma_b=0.05)
        t_model = TraceModel(fluorescence_model)

        probs = t_model.fluorescence_model.p_x_given_zs(trace, y)

        comb_matrix = transition_matrix._create_comb_matrix(y)
        comb_matrix_slanted = transition_matrix._create_comb_matrix(
            y,
            slanted=True)

        def c_transition_matrix_2(p_on, p_off):
            return transition_matrix.create_transition_matrix(
                y, p_on, p_off,
                comb_matrix,
                comb_matrix_slanted)

        transition_mat = c_transition_matrix_2(p_on, p_off)
        p_initial = transition_matrix.p_initial(y, transition_mat)
        likelihood = t_model.get_likelihood(
            probs,
            transition_mat,
            p_initial)

        # need to flip to positive value for grad descent
        return -1 * likelihood

    unit_grad_jit = jax.jit(
        jax.value_and_grad(
            likelihood_func,
            argnums=(0, 1, 2, 3)))

    return unit_grad_jit

def _initial_guesses(mu_min, y, trace, mu_b_guess=200, sigma=0.05):
    mus = jnp.linspace(mu_min, jnp.max(trace), 100)
    p_s = jnp.linspace(1e-4, 0.1, 20)
    
    bound_likelihood = lambda mu, p_on, p_off: _likelihood_func(y=y, p_on=p_on, 
        p_off=p_off, mu=mu, sigma=sigma, trace=trace, mu_b_guess = mu_b_guess)
    
    result = jax.vmap(jax.vmap(jax.vmap(bound_likelihood,
        in_axes=(0,None,None)),
        in_axes=(None,0,None)),
        in_axes=(None,None,0)) (mus, p_s, p_s)
    
    ig_index = jnp.where(result == jnp.min(result))
   
    return p_s[ig_index[0]], p_s[ig_index[1]], mus[ig_index[2]]