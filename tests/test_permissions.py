import types
import matterbot


class FakeUsers:
    def __init__(self, roles):
        self._roles = roles
    def get_user(self, userid):
        return {"roles": self._roles, "username": "u"}


class FakeDriver:
    def __init__(self, roles):
        self.users = FakeUsers(roles)


def make(roles, botadmins, botoperators):
    matterbot.options = types.SimpleNamespace(
        Matterbot={"botadmins": botadmins, "botoperators": botoperators},
        Modules={}, debug=False)
    mgr = object.__new__(matterbot.MattermostManager)
    mgr.mmDriver = FakeDriver(roles)
    return mgr


def test_operator_true_for_botoperator_id():
    assert make("system_user", ["adminid"], ["opid"]).isoperator("opid") is True


def test_operator_true_for_admin_superset():
    assert make("system_user", ["adminid"], []).isoperator("adminid") is True


def test_operator_true_for_role_name():
    assert make("system_user team_admin", [], ["team_admin"]).isoperator("x") is True


def test_operator_false_for_plain_user():
    assert make("system_user", ["adminid"], ["opid"]).isoperator("rando") in (False, None)


def test_should_exit_after_ws_true_when_requested():
    mgr = object.__new__(matterbot.MattermostManager)
    mgr._shutdown_requested = True
    assert matterbot.MattermostManager._should_exit_after_ws(mgr) is True


def test_should_exit_after_ws_false_by_default():
    mgr = object.__new__(matterbot.MattermostManager)
    mgr._shutdown_requested = False
    assert matterbot.MattermostManager._should_exit_after_ws(mgr) is False
