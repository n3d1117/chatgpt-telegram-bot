from typing import Any, Callable, List, TypeVar, cast
import pluggy

HOOK_NAMESPACE = "pluggy_chatgtp_telegram_bot"
PROJECT_NAME = "pluggy_chatgtp_telegram_bot"

hook_spec = pluggy.HookspecMarker(HOOK_NAMESPACE)
hook_impl = pluggy.HookimplMarker(HOOK_NAMESPACE)


class PluggySpecs:
    @hook_spec
    def get_spec(self) -> Any:
        pass

    @hook_spec
    async def run(arguments) -> Any:
        pass
