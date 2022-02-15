# -*- coding: utf-8 -*-


def component_from_data(data, message):
    if data.get('type') == 1:
        return ActionRow(data=data)
    elif data.get('type') == 2:
        return Button(data=data, message=message)
    elif data.get('type') == 3:
        return SelectMenu(data=data, message=message)
    elif data.get('type') == 4:
        return TextInput(data=data, message=message)

class ActionRow:
    def __init__(self, *, data):
        self.data = data

class Button:
    """Represents a message button (type=2)

    Attributes
    -----------
    """

    __slots__ = ('type', 'style', 'label', 'emoji', 'custom_id', 'url', 'disabled', 'message')

    def __init__(self, *, data:dict, message):
        self.type = data.get('type')
        self.style = data.get('style')
        self.label = data.get('label')
        self.emoji = data.get('emoji')
        self.custom_id = data.get('custom_id')
        self.url = data.get('url')
        self.disabled = data.get('disabled', False)
        self.message = message

class SelectMenu:
    """Represents a message Select menu (type=3)

    Attributes
    -----------
    """

    __slots__ = ('type', 'custom_id', 'options', 'placeholder', 'min_values', 'max_values', 'disabled', 'message')

    def __init__(self, *, data, message):
        self.type = data.get('type')
        self.custom_id = data.get('custom_id')
        self.options = data.get('options')
        self.placeholder = data.get('placeholder')
        self.min_values = data.get('min_values', 1)
        self.max_values = data.get('max_values', 1)
        self.disabled = data.get('disabled', False)
        self.message = message

class TextInput:
    """
    Represents a message text input (type=4)

    Attributes
    -----------
    """

    __slots__ = ('type', 'label', 'placeholder', 'style', 'custom_id', 'min_length', 'max_length', 'required', 'value', 'message')

    def __init__(self, *, data, message):
        self.type = data.get('type')
        self.label = data.get('label')
        self.placeholder = data.get('placeholder')
        self.style = data.get('style')
        self.custom_id = data.get('custom_id')
        self.min_length = data.get('min_length')
        self.max_length = data.get('max_length')
        self.required = data.get('required', False)
        self.value = data.get('value')
        self.message = message