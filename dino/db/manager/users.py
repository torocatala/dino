# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dino.db.manager.base import BaseManager
from dino.environ import GNEnvironment
from dino import utils
from dino.config import ConfigKeys
from dino.exceptions import UnknownBanTypeException

import traceback
import logging

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class UserManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_users_for_room(self, room_id: str) -> list:
        users = self.env.db.users_in_room(room_id)
        output = list()

        for user_id, user_name in users.items():
            output.append({
                'uuid': user_id,
                'name': user_name
            })
        return output

    def kick_user(self, room_id: str, user_id: str) -> None:
        kick_activity = {
            'actor': {
                'id': '0',
                'displayName': utils.b64e('admin')
            },
            'verb': 'kick',
            'object': {
                'id': user_id,
                'displayName': utils.b64e(self.env.db.get_user_name(user_id))
            },
            'target': {
                'id': room_id,
                'displayName': utils.b64e(self.env.db.get_room_name(room_id)),
                'objectType': 'room',
                'url': '/chat'
            }
        }
        self.env.publish(kick_activity)

    def ban_user(self, user_id: str, target_id: str, duration: str, target_type: str, reason: str=None, banner_id: str=None) -> None:
        target_name = None

        if target_type == 'global':
            pass
        elif target_type == 'channel':
            target_name = self.env.db.get_channel_name(target_id)
        elif target_type == 'room':
            target_name = self.env.db.get_room_name(target_id)
        else:
            raise UnknownBanTypeException(target_type)

        ban_activity = {
            'actor': {
                'id': '0',
                'displayName': utils.b64e('admin')
            },
            'verb': 'ban',
            'object': {
                'id': user_id,
                'displayName': utils.b64e(self.env.db.get_user_name(user_id)),
                'summary': duration,
                'updated': utils.ban_duration_to_datetime(duration).strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            },
            'target': {
                'url': '/chat',
                'objectType': target_type
            }
        }

        if reason is not None:
            ban_activity['object']['content'] = reason
        if banner_id is not None:
            ban_activity['actor']['id'] = banner_id
        if target_name is not None:
            ban_activity['target']['id'] = target_id
            ban_activity['target']['displayName'] = utils.b64e(target_name)

        self.env.publish(ban_activity)

    def remove_ban(self, user_id: str, target_id: str, target_type: str) -> None:
        if target_type == 'global':
            self.env.db.remove_global_ban(user_id)
        elif target_type == 'channel':
            self.env.db.remove_channel_ban(target_id, user_id)
        elif target_type == 'room':
            self.env.db.remove_room_ban(target_id, user_id)
        else:
            raise UnknownBanTypeException(target_type)

    def get_banned_users(self) -> dict:
        return self.env.db.get_banned_users()

    def add_channel_admin(self, channel_id: str, user_id: str) -> None:
        self.env.db.set_admin(channel_id, user_id)

    def add_channel_owner(self, channel_id: str, user_id: str) -> None:
        self.env.db.set_owner_channel(channel_id, user_id)

    def add_room_moderator(self, room_id: str, user_id: str) -> None:
        self.env.db.set_moderator(room_id, user_id)

    def add_room_owner(self, room_id: str, user_id: str) -> None:
        self.env.db.set_owner(room_id, user_id)

    def remove_channel_admin(self, channel_id: str, user_id: str) -> None:
        self.env.db.remove_admin(channel_id, user_id)

    def remove_channel_owner(self, channel_id: str, user_id: str) -> None:
        self.env.db.remove_owner_channel(channel_id, user_id)

    def remove_room_moderator(self, room_id: str, user_id: str) -> None:
        self.env.db.remove_moderator(room_id, user_id)

    def remove_room_owner(self, room_id: str, user_id: str) -> None:
        self.env.db.remove_owner(room_id, user_id)

    def create_super_user(self, user_name: str, user_id: str) -> None:
        try:
            self.env.db.create_user(user_id, user_name)
            self.env.db.set_super_user(user_id)
        except Exception as e:
            logger.exception(traceback.format_exc())
            logger.error('could not create super user: %s' % str(e))

    def get_user(self, user_id: str) -> dict:
        user_name = self.env.db.get_user_name(user_id)
        return {
            'uuid': user_id,
            'name': utils.b64e(user_name)
        }

    def _get_user(self, user_id: str, user_name: str) -> dict:
        return {
            'uuid': user_id,
            'name': user_name
        }

    def get_super_users(self) -> dict:
        users = self.env.db.get_super_users()
        output = list()
        for user_id, user_name in users.items():
            output.append(self._get_user(user_id, user_name))
        return output
