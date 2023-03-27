def dmerge(updated: dict, updating: dict):
    """
    Merge two dictionaries and return the changes.

    Works similar to the `dict.update()` method, but returns a dictionary containing the keys 'add' and 'upd'
    with their respective added and updated keys from the second dictionary.

    :param updated: The dictionary that will be updated
    :type updated: dict
    :param updating: The dictionary that contains the new values
    :type updating: dict
    :return: A dictionary containing keys 'add' and 'upd' with their respective added and updated keys.
    :rtype: dict

    :Example:
    updated = {'a': 1, 'b': 2};
    updating = {'b': 3, 'c': 4}\n
    {'add': {'c': 4}, 'upd': {'b': {'old': 2, 'new': 3}}}
    """
    changes = {'add': {}, 'upd': {}}
    for k, v in updating.items():
        if k in updated:
            if updated[k] != v:
                changes['upd'][k] = {"old": updated[k], "new": v}
                updated[k] = v
        else:
            changes['add'][k] = v
            updated[k] = v
    return changes


def plist(objects):
    """
    Converts ['a', 'b', 'c'] into 'a, b and c'

    :param objects: The list of objects to be converted
    :type objects: list
    :return: A string representation of the list of objects in the desired format.
    :rtype: str
    """
    objects = [str(o) for o in objects]
    if len(objects) > 1:
        return f'{", ".join(objects[:-1])} and {objects[-1]}'
    else:
        return ' and '.join(objects)
