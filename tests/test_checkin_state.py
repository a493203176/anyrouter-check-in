import sys
from pathlib import Path
from types import SimpleNamespace

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from checkin import build_account_schedule, format_check_in_notification, generate_balance_hash, get_user_info


class StubClient:
	def __init__(self, payload):
		self.payload = payload

	def get(self, *args, **kwargs):
		return SimpleNamespace(status_code=200, json=lambda: self.payload)


def test_balance_hash_changes_when_quota_changes():
	before = {'account_1': {'quota': 100.0, 'used': 20.0}}
	after = {'account_1': {'quota': 125.0, 'used': 20.0}}

	assert generate_balance_hash(before) != generate_balance_hash(after)


def test_balance_hash_changes_when_used_quota_changes():
	before = {'account_1': {'quota': 100.0, 'used': 20.0}}
	after = {'account_1': {'quota': 100.0, 'used': 21.0}}

	assert generate_balance_hash(before) != generate_balance_hash(after)


def test_balance_hash_is_stable_for_equivalent_balances():
	left = {
		'account_2': {'quota': 50.0, 'used': 1.0},
		'account_1': {'quota': 100.0, 'used': 20.0},
	}
	right = {
		'account_1': {'used': 20.0, 'quota': 100.0},
		'account_2': {'used': 1.0, 'quota': 50.0},
	}

	assert generate_balance_hash(left) == generate_balance_hash(right)


def test_build_account_schedule_can_shuffle_without_losing_original_indexes():
	class StubRandom:
		def shuffle(self, items):
			items.reverse()

	accounts = ['agent1', 'agent2', 'agent3']

	assert build_account_schedule(accounts, shuffle=False) == [(0, 'agent1'), (1, 'agent2'), (2, 'agent3')]
	assert build_account_schedule(accounts, shuffle=True, rng=StubRandom()) == [
		(2, 'agent3'),
		(1, 'agent2'),
		(0, 'agent1'),
	]


def test_get_user_info_includes_group_in_display():
	client = StubClient(
		{
			'success': True,
			'data': {
				'quota': 56_155_000,
				'used_quota': 56_345_000,
				'group': 'core',
			},
		}
	)

	info = get_user_info(client, {}, 'https://example.test/api/user/self')

	assert info['group'] == 'core'
	assert info['display'] == ':money: Current balance: $112.31, Used: $112.69, Group: core'


def test_get_user_info_falls_back_to_group_name():
	client = StubClient({'success': True, 'data': {'group_name': 'vip'}})

	info = get_user_info(client, {}, 'https://example.test/api/user/self')

	assert info['group'] == 'vip'


def test_format_check_in_notification_includes_group():
	message = format_check_in_notification(
		{
			'name': 'Account 1',
			'group': 'core',
			'before_quota': 112.31,
			'before_used': 112.69,
			'after_quota': 112.31,
			'after_used': 112.69,
			'check_in_reward': 0,
			'usage_increase': 0,
			'balance_change': 0,
			'success': True,
		}
	)

	assert '用户分组: core' in message
