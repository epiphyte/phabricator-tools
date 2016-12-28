#!/usr/bin/python
"""Conduit helpers."""

from io import BytesIO
import json
from urllib.parse import urlencode, quote
import pycurl


class Factory:
    """Common case to create conduit-derived classes."""

    token = None
    host = None

    def create(self, obj_type):
        """Create an instance."""
        obj = obj_type()
        obj.token = self.token
        obj.host = self.host
        return obj


class ConduitBase(object):
    """Conduit common operations."""

    token = None
    host = None
    prefix = None

    def _build(self, name, value):
        """build a parameter for posting."""
        return name + "=" + value

    def _go(self, operator, params=None, manual_post=True):
        """run an operation."""
        if self.prefix is None:
            raise Exception("no prefix configured")
        return self._execute(self.prefix + "." + operator,
                             manual_post=manual_post,
                             parameters=params)

    def _encode_list(self, prefix, vals):
        """encode a list set."""
        idx = 0
        for elem in vals:
            yield self._build(prefix + "[" + str(idx) + "]", elem)
            idx = idx + 1

    def _encode_dict(self, prefix, vals, nested):
        """encode a dictionary."""
        for item in vals:
            key = item
            if nested:
                key = prefix + "[" + item + "]"
            for e in self._encode(key, vals[item], True):
                yield e

    def _encode(self, prefix, vals, child):
        """Encode data parameters."""
        if isinstance(vals, str):
            yield self._build(prefix, vals)
        else:
            if isinstance(vals, dict):
                for d in self._encode_dict(prefix, vals, child):
                    yield d
            else:
                for l in self._encode_list(prefix, vals):
                    yield l

    def _execute(self, endpoint, manual_post=True, parameters=None):
        """Execute a conduit query."""
        if self.token is None:
            raise Exception("no token given...")
        if self.host is None:
            raise Exception("no host given...")
        curl = pycurl.Curl()
        curl.setopt(curl.URL, self.host + "/api/" + endpoint)
        # post-data
        if manual_post:
            fields = []
            fields.append(self._build("api.token", self.token))
            if parameters is not None and len(parameters) > 0:
                for f in self._encode("", parameters, False):
                    fields.append(f)
            posting = "&".join(fields)
        else:
            params = parameters
            if params is None:
                params = {}
            params["api.token"] = self.token
            posting = urlencode(params)
        buf = BytesIO()
        curl.setopt(curl.POSTFIELDS, posting)
        curl.setopt(curl.WRITEDATA, buf)
        curl.perform()
        # and data back
        res = json.loads(buf.getvalue().decode("iso-8859-1"))
        errored = res["error_code"]
        if errored is None:
            return res["result"]
        else:
            raise Exception(res["error_info"])


class Diffusion(ConduitBase):
    """Diffusion queries."""

    def __init__(self):
        """init the instance."""
        self.prefix = "diffusion"

    def filecontent_by_path_branch(self, path, callsign, branch):
        """file content query/lookup."""
        return self._go("filecontentquery", {"path": path,
                                             "repository": "r" + callsign,
                                             "branch": branch})


class File(ConduitBase):
    """File queries."""

    def __init__(self):
        """Init the instance."""
        self.prefix = "file"

    def download(self, phid):
        """Download a file."""
        return self._go("download", {"phid": phid})


class Dashboard(ConduitBase):
    """Dashboard queries."""

    def __init__(self):
        """init the instance."""
        self.prefix = "dashboard"

    def edit_text(self, identifier, text):
        vals = {}
        vals["transactions[0][type]"] = "custom.text"
        vals["transactions[0][value]"] = quote(text)
        vals["objectIdentifier"] = identifier
        return self._go("panel.edit", vals, manual_post=True)


class Project(ConduitBase):
    """Project queries."""

    def __init__(self):
        """init the instance."""
        self.prefix = "project"

    def open(self):
        """Open projects."""
        return self._query({"status": "status-open"})

    def by_name(self, name):
        """get projects by name."""
        return self._query({"names": [name]})

    def _query(self, params=None):
        """Query projects."""
        return self._go("query", params)


class User(ConduitBase):
    """User implementation."""

    def __init__(self):
        """init the instance."""
        self.prefix = "user"

    def by_phids(self, phids):
        """user by phid."""
        return self._query({"phids": phids})

    def whoami(self):
        """get user information."""
        return self._go("whoami")

    def _query(self, params=None):
        """Query users."""
        return self._go("query", params)

    def query(self):
        """Query users."""
        return self._query()


class CalendarEvent(ConduitBase):
    """Calendar implementation."""

    def __init__(self):
        """init the instance."""
        self.prefix = "calendar.event"

    def upcoming_by_subscriber(self, user_phid):
        """get upcoming events."""
        return self._search_by_query("upcoming",
                                     {"constraints":
                                      {"subscribers": [user_phid]}})

    def _search_by_query(self, query, params=None):
        """search the calendar."""
        vals = {"queryKey": query}
        if params:
            for p in params:
                vals[p] = params[p]
        return self._go("search", vals)


class Conpherence(ConduitBase):
    """Conpherence implementation."""

    def __init__(self):
        """init the instance."""
        self.prefix = "conpherence"

    def updatethread(self, room, message):
        """Update a conpherence thread."""
        return self._go("updatethread", {"id": room, "message": message})

    def querythread_by_id(self, room_id):
        """query a thread by id."""
        return self._querythread({"ids": [room_id]})

    def querytransaction_by_phid_last(self, room_phid, last):
        """get a transaction by room and last count."""
        return self._go("querytransaction", {"roomPHID": room_phid,
                                             "limit": last})

    def querythread(self):
        """Query thread."""
        return self._querythread(None)

    def _querythread(self, params=None):
        return self._go("querythread", params)


class Phriction(ConduitBase):
    """Phriction implementation."""

    def __init__(self):
        """init the instance."""
        self.prefix = "phriction"

    def info(self, slug):
        """get information for a page/slug."""
        return self._go("info", {"slug": slug})

    def edit(self, slug, title, content):
        """edit a phriction page."""
        return self._go("edit",
                        params={"slug": slug,
                                "title": title,
                                "content": content},
                        manual_post=False)


class Maniphest(ConduitBase):
    """Maniphest implementation."""

    def __init__(self):
        """init the instance."""
        self.prefix = "maniphest"

    def comment_by_id(self, task_id, message):
        """comment on a task by using the id."""
        params = self._comment_params(task_id, message)
        return self._update(params)

    def open(self):
        """Open tasks."""
        return self._query(self._open_params())

    def invalid_by_id(self, task_id):
        """close as invalid by id."""
        return self._close_by_id(task_id, "invalid")

    def resolve_by_id(self, task_id):
        """resolve as closed by id."""
        return self._close_by_id(task_id, "resolved")

    def _close_by_id(self, task_id, status):
        """close a task by id."""
        params = self._comment_params(task_id, "marking closed")
        params["status"] = status
        return self._update(params)

    def open_and_subscribed(self, user_phid):
        """Open by project phid."""
        params = self._open_params()
        params["ccPHIDs"] = [user_phid]
        return self._query(params)

    def open_by_project_phid(self, project_phid):
        """Open by project phid."""
        params = self._open_params()
        params["projectPHIDs"] = [project_phid]
        return self._query(params)

    def _comment_params(self, task_id, message):
        """Comment parameters."""
        return {"id": task_id, "comments": message}

    def _open_params(self):
        """Open status parameter building."""
        return {"status": "status-open"}

    def _update(self, params=None):
        """task updates."""
        return self._go("update", params)

    def _query(self, params=None):
        """Query operations."""
        return self._go("query", params)
