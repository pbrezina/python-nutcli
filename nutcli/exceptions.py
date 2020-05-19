class TimeoutError(Exception):
    """
    Timeout error: operation did not finished in time.
    """

    def __init__(self, timeout, message):
        """
        :param timeout: Timeout in seconds.
        :type timeout: int
        :param message: Error message.
        :type message: str
        """
        super().__init__(message)
        self.timeout = timeout
