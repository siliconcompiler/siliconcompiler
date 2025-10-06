class SCRuntimeError(RuntimeError):
    def __init__(self, msg: str):
        super().__init__(msg)

        self.__msg = msg

    @property
    def msg(self) -> str:
        return self.__msg
