from db.sqlite import check_data_acc
from typing import Set


def get_ready_users() -> Set[int]:
    """Gets all user IDs with filled data, that are ready to run scanning.
    Returns:
        Set of user IDs or empty set
    """
    ready_users = set()
    for user in check_data_acc():
        user_id_acc = user[0]
        # Check for blank fields in account table except columns:
        # start_time, is_active, last_request, attempts
        if None not in user[:9]:
            ready_users.add(user_id_acc)
    return ready_users
