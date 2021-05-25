import logging

from dino.utils.activity_helper import ActivityBuilder

from dino import environ
from dino.config import ConfigKeys

logger = logging.getLogger(__name__)


class OnStartupDoneHooks(object):
    @staticmethod
    def publish_startup_done_event() -> None:
        if len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING, False):
            # assume we're testing
            return

        # if e.g. the staging environment is sharing online status state with e.g. the production
        # environment for easier live debugging, we don't want to send restart event when we restart
        # the staging environment
        if not environ.env.config.get(ConfigKeys.SEND_RESTART_EVENT, True):
            return

        if environ.env.node != 'web':
            # avoid publishing duplicate events by only letting the web node publish external events
            return

        json_event = ActivityBuilder.enrich({
            'verb': 'restart',
            'actor': {'id': '0'},
            'content': environ.env.config.get(ConfigKeys.ENVIRONMENT),
        })

        logger.debug('publishing restart-done event to external queue: %s' % str(json_event))
        environ.env.publish(json_event, external=True)


@environ.env.observer.on('on_startup_done')
def _on_startup_done(arg) -> None:
    OnStartupDoneHooks.publish_startup_done_event()
