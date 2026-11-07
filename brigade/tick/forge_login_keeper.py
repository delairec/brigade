from brigade.runtime import Runtime


class ForgeLoginKeeper:
    def __init__(self, forge: object):
        self.forge = forge
        self.environments: dict[str, dict] = {}

    def read_login_environment(self, request: dict, runtime: Runtime) -> dict:
        login = request["login"]
        if login in self.environments:
            return self.environments[login]
        answer = self.forge.read_login_environment(request, runtime)
        if answer["environment"] is not None:
            self.environments[login] = answer
        return answer

    def __getattr__(self, operation: str):
        return getattr(self.forge, operation)
