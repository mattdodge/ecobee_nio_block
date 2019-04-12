from datetime import timedelta
import json
import requests
from nio import Block
from nio.block import input, output
from nio.block.mixins import EnrichSignals, Persistence, Retry
from nio.command import command
from nio.modules.scheduler.job import Job
from nio.properties import StringProperty, VersionProperty, FloatProperty


@input('read', label='Read', default=True, order=0)
@input('set', label='Set Temp', order=1)
@output('temps', label='Temp Data', default=True, order=0)
@output('set_status', label='Set Status', order=1)
@command('fetch_thermostats')
class EcobeeThermostat(Retry, EnrichSignals, Persistence, Block):

    app_key = StringProperty(title='App Key', default='[[ECOBEE_APP_KEY]]')
    refresh_token = StringProperty(
        title='Initial Refresh Token', default='[[ECOBEE_REFRESH_TOKEN]]')
    desired_temp = FloatProperty(
        title='Desired Temperature', default='{{ $temp }}')
    version = VersionProperty('0.0.2')

    def __init__(self):
        super().__init__()
        self._auth_token = None
        self._refresh_token = None
        self._refresh_job = None

    def configure(self, context):
        super().configure(context)
        # Try to use the persisted refresh token, otherwise use the block
        # configuration's initial refresh token
        if self._refresh_token is None:
            self._refresh_token = self.refresh_token()
        self.refresh_auth_token()

    def start(self):
        super().start()
        self._refresh_job = Job(
            self.refresh_auth_token,
            timedelta(seconds=3000),
            True)

    def stop(self):
        if self._refresh_job:
            self._refresh_job.cancel()
        super().stop()

    def persisted_values(self):
        return ["_refresh_token"]

    def refresh_auth_token(self):
        self.logger.info("Fetching access token...")
        self.logger.debug("Using refresh token {}".format(self._refresh_token))
        token_body = requests.post(
            'https://api.ecobee.com/token',
            params={
                'grant_type': 'refresh_token',
                'code': self._refresh_token,
                'client_id': self.app_key(),
            },
        ).json()
        self._auth_token = token_body['access_token']
        self._refresh_token = token_body['refresh_token']
        self.logger.info("Fetched access token : {}".format(token_body))

    def before_retry(self, *args, **kwargs):
        super().before_retry(*args, **kwargs)
        self.refresh_auth_token()

    def process_signals(self, signals, input_id='read'):
        out_signals = []
        output_id = None
        for signal in signals:
            if input_id == 'read':
                output_id = 'temps'
                out_sig = self.get_output_signal(
                    self.fetch_thermostats(signal), signal)
            elif input_id == 'set':
                output_id = 'set_status'
                desired_temp = self.desired_temp(signal)
                out_sig = self.get_output_signal(
                    self.set_temp(desired_temp), signal)
            if out_sig:
                out_signals.append(out_sig)
        self.notify_signals(out_signals, output_id=output_id)

    def fetch_thermostats(self, signal=None):
        therms = self.execute_with_retry(
            self._make_ecobee_request,
            'thermostat',
            method='get',
            body={
                'selection': {
                    'selectionType': 'registered',
                    'selectionMatch': '',
                    'includeRuntime': True,
                    'includeSettings': True,
                }
            })
        return therms.json()

    def set_temp(self, temp):
        self.logger.info("Setting thermostat to {} degrees".format(temp))
        result = self.execute_with_retry(
            self._make_ecobee_request,
            'thermostat',
            method='post',
            body={
                "selection": {
                    "selectionType": "registered",
                    "selectionMatch": ""
                },
                "functions": [
                    {
                        "type": "setHold",
                        "params": {
                            "holdType": "nextTransition",
                            "heatHoldTemp": int(temp * 10),
                            "coolHoldTemp": int(temp * 10)
                        }
                    }
                ]
            })
        return result.json()

    def _make_ecobee_request(self, endpoint, method='get', body={}):
        headers = {
            'Authorization': 'Bearer {}'.format(self._auth_token),
        }
        params = {
            'format': 'json',
        }
        if method == 'get':
            params['body'] = json.dumps(body)
            post_body = None
        else:
            post_body = body

        resp = getattr(requests, method)(
            'https://api.ecobee.com/1/{}'.format(endpoint),
            headers=headers,
            params=params,
            json=post_body,
        )
        resp.raise_for_status()
        return resp
