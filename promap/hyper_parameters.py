class HyperParameters:
    """Hyperparameters to control the maximum likelihood optimization.

    Args:

        gradient_step_size (float):

            The step size for the gradient optimization of the parameters.

        num_guesses (int):

            The number of parameter guesses to start maximum likelihood
            optimization from.

        epoch_length (int):

            The length of an "epoch". This is used to break the optimization
            into smaller stretches (epochs). Convergence is tested for at the
            end of each epoch.

        max_x (``int``):

            The maximal x value to consider for discretizing x.
    """

    def __init__(
        self,
        min_y=1,
        gradient_step_size=1e-3,
        num_guesses=5,
        epoch_length=1000,
        is_done_limit=1e-5,
        mu_gradient_step_size=1e-3,
        distribution_threshold=1e-1,
        max_x=None,
        num_x_bins=1024,
        p_outlier=0.1,
    ):
        self.min_y = min_y
        self.gradient_step_size = gradient_step_size
        self.num_guesses = num_guesses
        self.epoch_length = epoch_length
        self.is_done_limit = is_done_limit
        self.mu_gradient_step_size = mu_gradient_step_size
        self.distribution_threshold = distribution_threshold
        self.max_x = max_x
        self.num_x_bins = num_x_bins
        self.p_outlier = p_outlier
