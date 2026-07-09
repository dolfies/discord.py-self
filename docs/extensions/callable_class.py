from __future__ import annotations

from typing import Tuple

from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.locale import _

try:
    from sphinxcontrib_trio import ExtendedPyMethod as BasePyMethod
except ImportError:
    from sphinx.domains.python import PyMethod as BasePyMethod


def _normalise_class_name(class_name: str, module_name: str) -> str:
    if module_name and class_name.startswith(module_name + '.'):
        return class_name[len(module_name) + 1 :]

    return class_name


def _display_name(signode: addnodes.desc_signature) -> str:
    fullname = signode.get('fullname', '')
    class_name = signode.get('class') or fullname.removesuffix('.__call__')
    return _normalise_class_name(class_name, signode.get('module', ''))


def _remove_call_prefix(signode: addnodes.desc_signature, class_name: str) -> None:
    possible_prefixes = {
        class_name,
        signode.get('class', ''),
    }

    for child in list(signode.children):
        if not isinstance(child, addnodes.desc_addname):
            continue

        prefix = child.astext().removesuffix('.')
        if prefix in possible_prefixes or any(prefix.endswith('.' + name) for name in possible_prefixes if name):
            signode.remove(child)


def _replace_call_name(signode: addnodes.desc_signature, class_name: str) -> None:
    for child in signode.findall(addnodes.desc_name):
        if child.astext() == '__call__':
            child.replace_self(addnodes.desc_name(class_name, class_name))
            return


def _rewrite_call_signature(signode: addnodes.desc_signature) -> None:
    if not signode.get('fullname', '').endswith('.__call__'):
        return

    class_name = _display_name(signode)
    if not class_name:
        return

    _remove_call_prefix(signode, class_name)
    _replace_call_name(signode, class_name)


class CallableClassMethod(BasePyMethod):
    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> Tuple[str, str]:
        result = super().handle_signature(sig, signode)
        _rewrite_call_signature(signode)
        return result

    def get_index_text(self, modname: str, name_cls: Tuple[str, str]) -> str:
        name, original_class_name = name_cls
        if name.endswith('.__call__'):
            class_name = name.removesuffix('.__call__')
            full_class_name = class_name
            if modname and self.env.config.add_module_names and not class_name.startswith(modname + '.'):
                full_class_name = f'{modname}.{class_name}'

            display_name = _normalise_class_name(class_name, modname)
            return _('%s() (%s method)') % (display_name, full_class_name)

        return super().get_index_text(modname, (name, original_class_name))


def setup(app: Sphinx):
    app.add_directive_to_domain('py', 'method', CallableClassMethod, override=True)
    return {'parallel_read_safe': True}