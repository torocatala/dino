import traceback
import logging
import time
import sys
import activitystreams as as_parser

from functools import wraps
from datetime import datetime
from uuid import uuid4 as uuid

from dino.wio import validation
from dino.wio import environ
from dino.wio import utils
from dino.exceptions import NoSuchUserException
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import ErrorCodes

logger = logging.getLogger()


def wio_pre_process(validation_name, should_validate_request=True):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*a, **k):
            def _pre_process(*args, **kwargs):
                if not hasattr(validation.request, validation_name):
                    raise RuntimeError('no such attribute on validation.request: %s' % validation_name)

                try:
                    data = args[0]
                    if 'actor' not in data:
                        data['actor'] = dict()

                    # let the server determine the publishing time of the event, not the client
                    # use default time format, since activity streams only accept RFC3339 format
                    data['published'] = datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                    data['id'] = str(uuid())

                    if should_validate_request:
                        data['actor']['id'] = str(environ.env.session.get(SessionKeys.user_id.value))
                        user_name = environ.env.session.get(SessionKeys.user_name.value)
                        if user_name is None or len(user_name.strip()) == 0:
                            try:
                                user_name = environ.env.db.get_user_name(data['actor']['id'])
                            except NoSuchUserException:
                                error_msg = '[%s] no user found for user_id "%s" in session' % \
                                            (validation_name, str(data['actor']['id']))
                                logger.error(error_msg)
                                return ErrorCodes.NO_USER_IN_SESSION, error_msg
                        data['actor']['displayName'] = utils.b64e(user_name)

                    activity = as_parser.parse(data)

                    # the login request will not have user id in session yet, which this would check
                    if should_validate_request:
                        is_valid, error_msg = validation.request.validate_request(activity)
                        if not is_valid:
                            logger.error('[%s] validation failed, error message: %s' % (validation_name, str(error_msg)))
                            return ErrorCodes.VALIDATION_ERROR, error_msg

                    is_valid, status_code, message = getattr(validation.request, validation_name)(activity)
                    if is_valid:
                        all_ok = True
                        if validation_name in environ.env.event_validator_map:
                            for validator in environ.env.event_validator_map[validation_name]:
                                all_ok, status_code, msg = validator(data, activity)
                                if not all_ok:
                                    logger.warning(
                                            '[%s] validator "%s" failed: %s' %
                                            (validation_name, str(validator), str(msg)))
                                    break

                        if all_ok:
                            args = (data, activity)
                            status_code, message = view_func(*args, **kwargs)

                except Exception as e:
                    logger.error('%s: %s' % (validation_name, str(e)))
                    logger.exception(traceback.format_exc())
                    environ.env.stats.incr('event.' + validation_name + '.exception')
                    environ.env.capture_exception(sys.exc_info())
                    return ErrorCodes.UNKNOWN_ERROR, str(e)

                if status_code == 200:
                    environ.env.stats.incr('event.' + validation_name + '.count')
                else:
                    environ.env.stats.incr('event.' + validation_name + '.error')
                    logger.warning('in decorator for %s, status_code: %s, message: %s' %
                                (validation_name, status_code, str(message)))
                return status_code, message

            start = time.time()
            exception_occurred = False
            try:
                environ.env.stats.incr('event.' + validation_name + '.count')
                return _pre_process(*a, **k)
            except:
                exception_occurred = True
                environ.env.stats.incr('event.' + validation_name + '.exception')
                raise
            finally:
                if not exception_occurred:
                    environ.env.stats.timing('event.' + validation_name, (time.time()-start)*1000)
        return decorator
    return factory
