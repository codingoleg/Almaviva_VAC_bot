from db.sqlite import check_data_acc, check_data_person
from typing import Set


def get_ready_users() -> Set[int]:
    """Gets all user IDs with filled data, that are ready to run scanning.
    Returns:
        Set of user IDs or empty set
    """
    ready_users = set()
    for user in check_data_acc():
        user_id_acc = user[0]
        # Check for blank fields in account table except 3 last columns
        if None not in user[:10]:
            num_of_persons = user[3]
            for person in check_data_person(num_of_persons):
                # Check for blank fields in person tables
                user_id_person = person[0]
                if user_id_acc == user_id_person and None not in person:
                    ready_users.add(user_id_acc)
    return ready_users
