"""
Sony Bravia RC API.

By Antonio Parraga Navarro dedicated to Isabel.

Updated by Gerard for use in Home Assistant.
    Changes:
    * Use Pre-shared key (PSK) instead of connecting with a pin and the use of a cookie.
    * Added function to calculate the media position.
"""
import base64
import collections
import datetime
import json
import logging
import socket
import struct

import requests

TIMEOUT = 8  # timeout in seconds

_LOGGER = logging.getLogger(__name__)


class BraviaRC(object):
    """Representation of a Sony Bravia TV."""

    def __init__(
        self, host, psk, mac=None
    ):  # mac address is optional but necessary if we want to turn on the TV
        """Initialize the Sony Bravia RC class."""
        self._host = host
        self._psk = psk
        self._mac = mac
        self._cookies = None
        self._commands = []
        self._content_mapping = []

    def _jdata_build(self, method, params=None):
        if params:
            ret = json.dumps(
                {"method": method, "params": [params], "id": 1, "version": "1.0"}
            )
        else:
            ret = json.dumps(
                {"method": method, "params": [], "id": 1, "version": "1.0"}
            )
        return ret

    def connect(self, pin, clientid, nickname):
        """Connect to TV and get authentication cookie.

        Parameters
        ---------
        pin: str
            Pin code show by TV (or 0000 to get Pin Code).
        clientid: str
            Client ID.
        nickname: str
            Client human friendly name.
        Returns
        -------
        bool
            True if connected.
        """
        authorization = json.dumps(
            {
                "method": "actRegister",
                "params": [
                    {"clientid": clientid, "nickname": nickname, "level": "private"},
                    [{"value": "yes", "function": "WOL"}],
                ],
                "id": 1,
                "version": "1.0",
            }
        ).encode("utf-8")

        headers = {}
        if pin:
            username = ""
            base64string = (
                base64.encodebytes(("%s:%s" % (username, pin)).encode())
                .decode()
                .replace("\n", "")
            )
            headers["Authorization"] = "Basic %s" % base64string
            headers["Connection"] = "keep-alive"

        try:
            response = requests.post(
                "http://" + self._host + "/sony/accessControl",
                data=authorization,
                headers=headers,
                timeout=TIMEOUT,
            )
            response.raise_for_status()

        except requests.exceptions.HTTPError as exception_instance:
            _LOGGER.exception("[W] HTTPError: " + str(exception_instance))
            return False

        except requests.exceptions.Timeout as exception_instance:
            _LOGGER.exception("[W] Timeout occurred: " + str(exception_instance))
            return False

        except Exception as exception_instance:  # pylint: disable=broad-except
            _LOGGER.exception("[W] Exception: " + str(exception_instance))
            return False

        else:
            resp = response.json()
            _LOGGER.debug(json.dumps(resp, indent=4))
            if resp is None or not resp.get("error"):
                self._cookies = response.cookies
                return True

        return False

    def is_connected(self):
        """Check if connection is established."""
        if self._cookies is None:
            return False
        else:
            return True

    def _wakeonlan(self):
        if self._mac is not None:
            addr_byte = self._mac.split(":")
            hw_addr = struct.pack(
                "BBBBBB",
                int(addr_byte[0], 16),
                int(addr_byte[1], 16),
                int(addr_byte[2], 16),
                int(addr_byte[3], 16),
                int(addr_byte[4], 16),
                int(addr_byte[5], 16),
            )
            msg = b"\xff" * 6 + hw_addr * 16
            socket_instance = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socket_instance.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            socket_instance.sendto(msg, ("<broadcast>", 9))
            socket_instance.close()

    def send_req_ircc(self, params, log_errors=True):
        """Send an IRCC command via HTTP to Sony Bravia."""
        if params is None:
            return False
        headers = {
            "X-Auth-PSK": self._psk,
            "SOAPACTION": '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"',
        }
        data = (
            '<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org'
            + '/soap/envelope/" '
            + 's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
            + "<u:X_SendIRCC "
            + 'xmlns:u="urn:schemas-sony-com:service:IRCC:1"><IRCCCode>'
            + params
            + "</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>"
        ).encode("UTF-8")
        try:
            response = requests.post(
                "http://" + self._host + "/sony/IRCC",
                headers=headers,
                data=data,
                timeout=TIMEOUT,
            )
        except requests.exceptions.HTTPError as exception_instance:
            if log_errors:
                _LOGGER.error("HTTPError: " + str(exception_instance))

        except requests.exceptions.Timeout as exception_instance:
            if log_errors:
                _LOGGER.error("Timeout occurred: " + str(exception_instance))

        except Exception as exception_instance:  # pylint: disable=broad-except
            if log_errors:
                _LOGGER.error("Exception: " + str(exception_instance))
        else:
            content = response.content
            return content

    def bravia_req_json(self, url, params, log_errors=True):
        """Send request command via HTTP json to Sony Bravia."""
        try:
            response = requests.post(
                "http://" + self._host + "/" + url,
                data=params.encode("UTF-8"),
                headers={"X-Auth-PSK": self._psk},
                timeout=TIMEOUT,
            )
        except requests.exceptions.HTTPError as exception_instance:
            if log_errors:
                _LOGGER.error("HTTPError: " + str(exception_instance))

        except requests.exceptions.Timeout as exception_instance:
            if log_errors:
                _LOGGER.error("Timeout occurred: " + str(exception_instance))

        except Exception as exception_instance:  # pylint: disable=broad-except
            if log_errors:
                _LOGGER.error("Exception: " + str(exception_instance))

        else:
            response = json.loads(response.content.decode("utf-8"))
            if "error" in response and log_errors:
                _LOGGER.error(
                    "Invalid response: %s\n  request path: %s\n  request params: %s"
                    % (response, url, params)
                )
            return response

    def send_command(self, command):
        """Send command to the TV."""
        self.send_req_ircc(self.get_command_code(command))

    def load_app_list(self):
        """Get the list of installed apps."""
        resp = self.bravia_req_json(
            "sony/appControl", self._jdata_build("getApplicationList")
        )
        if resp.get("error"):
            _LOGGER.error("ERROR: %s" % resp.get("error"))
        else:
            return resp.get("result")[0]

    def open_app(self, uri):
        """Open app with given uri."""
        resp = self.bravia_req_json(
            "sony/appControl", self._jdata_build("setActiveApp", {"uri": uri})
        )
        if resp.get("error"):
            _LOGGER.error("ERROR: %s" % resp.get("error"))

    def get_source(self, source):
        """Return list of sources."""
        original_content_list = []
        content_index = 0
        while True:
            resp = self.bravia_req_json(
                "sony/avContent",
                self._jdata_build(
                    "getContentList", {"source": source, "stIdx": content_index}
                ),
            )
            if not resp.get("error"):
                if len(resp.get("result")[0]) == 0:
                    break
                else:
                    content_index = resp.get("result")[0][-1]["index"] + 1
                original_content_list.extend(resp.get("result")[0])
            else:
                break
        return original_content_list

    def load_source_list(self):
        """Load source list from Sony Bravia."""
        original_content_list = []
        resp = self.bravia_req_json(
            "sony/avContent", self._jdata_build("getSourceList", {"scheme": "tv"})
        )
        if not resp.get("error"):
            results = resp.get("result")[0]
            for result in results:
                # tv:dvbc = via cable, tv:dvbt = via DTT, tv:dvbs = via satellite
                # tv:isdbgt = Brazilian Digital TV standard, tv:atsct = via atsct
                # tv:analog = via analog input
                if result["source"] in [
                    "tv:dvbc",
                    "tv:dvbt",
                    "tv:dvbs",
                    "tv:isdbt",
                    "tv:isdbbs",
                    "tv:isdbcs",
                    "tv:isdbgt",
                    "tv:atsct",
                    "tv:analog",
                ]:
                    original_content_list.extend(self.get_source(result["source"]))

        resp = self.bravia_req_json(
            "sony/avContent", self._jdata_build("getSourceList", {"scheme": "extInput"})
        )
        if not resp.get("error"):
            results = resp.get("result")[0]
            for result in results:
                if result["source"] in (
                    "extInput:hdmi",
                    "extInput:composite",
                    "extInput:component",
                    "extInput:cec",
                ):  # physical inputs
                    resp = self.bravia_req_json(
                        "sony/avContent", self._jdata_build("getContentList", result)
                    )
                    if not resp.get("error"):
                        original_content_list.extend(resp.get("result")[0])

        return_value = collections.OrderedDict()
        for content_item in original_content_list:
            return_value[content_item["title"]] = content_item["uri"]
        return return_value

    def get_playing_info(self):
        """Get information on program that is shown on TV."""
        return_value = {}
        resp = self.bravia_req_json(
            "sony/avContent", self._jdata_build("getPlayingContentInfo", None), False
        )
        if resp is not None and not resp.get("error"):
            playing_content_data = resp.get("result")[0]
            return_value["programTitle"] = playing_content_data.get("programTitle")
            return_value["title"] = playing_content_data.get("title")
            return_value["programMediaType"] = playing_content_data.get(
                "programMediaType"
            )
            return_value["dispNum"] = playing_content_data.get("dispNum")
            return_value["source"] = playing_content_data.get("source")
            return_value["uri"] = playing_content_data.get("uri")
            return_value["durationSec"] = playing_content_data.get("durationSec")
            return_value["startDateTime"] = playing_content_data.get("startDateTime")
        return return_value

    def get_power_status(self):
        """Get power status being off, active or standby."""
        return_value = "off"  # by default the TV is turned off
        try:
            resp = self.bravia_req_json(
                "sony/system", self._jdata_build("getPowerStatus", None), False
            )
            if resp is not None and not resp.get("error"):
                power_data = resp.get("result")[0]
                return_value = power_data.get("status")
        except:  # pylint: disable=broad-except  # noqa: E722
            pass
        return return_value

    def _refresh_commands(self):
        resp = self.bravia_req_json(
            "sony/system", self._jdata_build("getRemoteControllerInfo", None)
        )
        if not resp.get("error"):
            self._commands = resp.get("result")[1]
        else:
            error = resp.get("error")
            if "not power-on" not in error:
                _LOGGER.error("JSON request error: " + json.dumps(resp, indent=4))

    def get_command_code(self, command_name):
        """Get command code."""
        if len(self._commands) == 0:
            self._refresh_commands()
        for command_data in self._commands:
            if command_data.get("name") == command_name:
                return command_data.get("value")
        return None

    def get_volume_info(self):
        """Get volume info."""
        resp = self.bravia_req_json(
            "sony/audio",
            self._jdata_build("getVolumeInformation", None),
            log_errors=False,
        )
        error = resp.get("error")
        if not error:
            results = resp.get("result")[0]
            for result in results:
                if result.get("target") == "speaker":
                    return result
        elif 40005 not in error:  # 40005 = "Display is Turned off"
            _LOGGER.error("JSON request error:" + json.dumps(resp, indent=4))
        return None

    def get_system_info(self):
        """Get info on TV."""
        return_value = {}
        resp = self.bravia_req_json(
            "sony/system", self._jdata_build("getSystemInformation", None)
        )
        if resp is not None and not resp.get("error"):
            # print('=>', resp, '<=')
            system_content_data = resp.get("result")[0]
            return_value["name"] = system_content_data.get("name")
            return_value["model"] = system_content_data.get("model")
            return_value["mac"] = system_content_data.get("mac")
            return_value["serial"] = system_content_data.get("serial")
            return_value["language"] = system_content_data.get("language")
        return return_value

    def get_network_info(self):
        """Get info on network."""
        return_value = {}
        resp = self.bravia_req_json(
            "sony/system", self._jdata_build("getNetworkSettings", None)
        )
        if resp is not None and not resp.get("error"):
            # print('=>', resp, '<=')
            network_content_data = resp.get("result")[0]
            return_value["mac"] = network_content_data[0]["hwAddr"]
            return_value["ip"] = network_content_data[0]["ipAddrV4"]
            return_value["gateway"] = network_content_data[0]["gateway"]
        return return_value

    def get_current_external_input_status(self):
        """Get current external input status."""
        return_value = []
        resp = self.bravia_req_json(
            "sony/avContent",
            self._jdata_build("getCurrentExternalInputsStatus", None),
            log_errors=False,
        )
        if resp is not None and not resp.get("error"):
            return_value = resp.get("result")[0]
        return return_value

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        # API expects string int value within 0..100 range.
        api_volume = str(int(round(volume * 100)))
        self.bravia_req_json(
            "sony/audio",
            self._jdata_build(
                "setAudioVolume", {"target": "speaker", "volume": api_volume}
            ),
        )

    def turn_on(self):
        """Turn the media player on."""
        self._wakeonlan()

    def turn_on_command(self):
        """Turn the media player on using command.

        Only confirmed working on Android, can be used when WOL is not available.
        """
        if self.get_power_status() != "active":
            self.send_req_ircc(self.get_command_code("TvPower"))
            self.bravia_req_json(
                "sony/system",
                self._jdata_build("setPowerStatus", {"status": True}),
                log_errors=False,
            )

    def turn_off(self):
        """Turn off media player."""
        self.send_req_ircc(self.get_command_code("PowerOff"))

    def turn_off_command(self):
        """Turn off media player using the rest-api for Android TV."""
        self.bravia_req_json(
            "sony/system", self._jdata_build("setPowerStatus", {"status": False})
        )

    def volume_up(self):
        """Volume up the media player."""
        self.send_req_ircc(self.get_command_code("VolumeUp"))

    def volume_down(self):
        """Volume down media player."""
        self.send_req_ircc(self.get_command_code("VolumeDown"))

    def mute_volume(self):
        """Send mute command."""
        self.send_req_ircc(self.get_command_code("Mute"))

    def select_source(self, source):
        """Set the input source."""
        if len(self._content_mapping) == 0:
            self._content_mapping = self.load_source_list()
        if source in self._content_mapping:
            uri = self._content_mapping[source]
            self.play_content(uri)

    def play_content(self, uri):
        """Play content by URI."""
        self.bravia_req_json(
            "sony/avContent", self._jdata_build("setPlayContent", {"uri": uri})
        )

    def media_play(self):
        """Send play command."""
        self.send_req_ircc(self.get_command_code("Play"))

    def media_pause(self):
        """Send media pause command to media player."""
        self.send_req_ircc(self.get_command_code("Pause"))

    def media_tvpause(self):
        """Send tv pause command to media player."""
        self.send_req_ircc(self.get_command_code("TvPause"))

    def media_next_track(self):
        """Send next track command."""
        self.send_req_ircc(self.get_command_code("Next"))

    def media_previous_track(self):
        """Send the previous track command."""
        self.send_req_ircc(self.get_command_code("Prev"))

    def add_seconds(self, tm, secs):
        """Add seconds to time (HH:MM:SS)."""
        fulldate = datetime.datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
        fulldate = fulldate + datetime.timedelta(seconds=secs)
        return fulldate.time()

    def playing_time(self, startdatetime, durationsec):
        """Return starttime and endtime (HH:MM) of TV program."""
        # startdatetime format 2017-03-24T00:00:00+0100
        return_value = {}
        startdatetime = startdatetime[:19]  # Remove timezone

        starttime = datetime.datetime.strptime(
            startdatetime, "%Y-%m-%dT%H:%M:%S"
        ).time()
        endtime = self.add_seconds(starttime, durationsec)

        return_value["start_time"] = starttime.strftime("%H:%M")
        return_value["end_time"] = endtime.strftime("%H:%M")
        return return_value
