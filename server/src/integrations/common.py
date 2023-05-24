class Integration:
    def params(self):
        """Returns the parameters necessary to de-serialize this object from the datastore"""
        ...

    def __enter__(self):
        """
        Returns an instance of this integration's api. Any authorization should be handled here -- tokens should be valid once `return` is made.
        """
        ...

    def __exit__(self, exception_type, exception_value, traceback):
        """
        Cleans up any resources used by this integration.
        """
        if exception_type is not None:
            return False

        return True
