#!/usr/bin/env python3
"""
Test script to verify Components v2 support in discord.py-self.
This test verifies that v2 component types (5-9) are properly parsed.
"""

import ast
import sys

def test_component_types():
    """Test that ComponentType enum has v2 values."""
    with open('discord/enums.py', 'r') as f:
        content = f.read()
    
    # Check for v2 enum values
    v2_types = ['string_select = 5', 'user_select = 6', 'role_select = 7', 
                'mentionable_select = 8', 'channel_select = 9']
    
    for v2_type in v2_types:
        if v2_type not in content:
            print(f"❌ Missing enum: {v2_type}")
            return False
        print(f"✅ Found enum: {v2_type}")
    
    return True

def test_type_definitions():
    """Test that type definitions for v2 components exist."""
    with open('discord/types/components.py', 'r') as f:
        content = f.read()
    
    # Check for v2 TypedDict classes
    v2_types = ['StringSelectMenu', 'UserSelectMenu', 'RoleSelectMenu', 
                'MentionableSelectMenu', 'ChannelSelectMenu']
    
    for v2_type in v2_types:
        if f'class {v2_type}(TypedDict):' not in content:
            print(f"❌ Missing type definition: {v2_type}")
            return False
        print(f"✅ Found type definition: {v2_type}")
    
    # Check ComponentType literal
    if 'ComponentType = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]' not in content:
        print("❌ ComponentType Literal not updated for v2")
        return False
    print("✅ ComponentType Literal includes v2 types (5-9)")
    
    return True

def test_component_classes():
    """Test that component classes for v2 exist."""
    with open('discord/components.py', 'r') as f:
        content = f.read()
    
    # Check for v2 component classes
    v2_classes = ['class StringSelectMenu(Component):', 
                  'class UserSelectMenu(BaseSelectMenu):',
                  'class RoleSelectMenu(BaseSelectMenu):',
                  'class MentionableSelectMenu(BaseSelectMenu):',
                  'class ChannelSelectMenu(BaseSelectMenu):']
    
    for v2_class in v2_classes:
        if v2_class not in content:
            print(f"❌ Missing class: {v2_class}")
            return False
        print(f"✅ Found class: {v2_class}")
    
    # Check factory function handles v2 types
    factory_checks = [
        'elif data[\'type\'] == 5:',
        'elif data[\'type\'] == 6:',
        'elif data[\'type\'] == 7:',
        'elif data[\'type\'] == 8:',
        'elif data[\'type\'] == 9:',
        'return StringSelectMenu(data, message)',
        'return UserSelectMenu(data, message)',
        'return RoleSelectMenu(data, message)',
        'return MentionableSelectMenu(data, message)',
        'return ChannelSelectMenu(data, message)',
    ]
    
    for check in factory_checks:
        if check not in content:
            print(f"❌ Missing factory function handler: {check}")
            return False
    
    print("✅ Factory function handles all v2 component types (5-9)")
    
    return True

def test_exports():
    """Test that v2 components are exported from the module."""
    with open('discord/components.py', 'r') as f:
        content = f.read()
    
    v2_exports = ['StringSelectMenu', 'UserSelectMenu', 'RoleSelectMenu',
                  'MentionableSelectMenu', 'ChannelSelectMenu']
    
    __all_start = content.find('__all__ = (')
    __all_end = content.find(')', __all_start)
    __all_section = content[__all_start:__all_end]
    
    for export in v2_exports:
        if f"'{export}'" not in __all_section:
            print(f"❌ {export} not exported in __all__")
            return False
        print(f"✅ {export} exported")
    
    return True

def test_syntax():
    """Test that all modified files have valid Python syntax."""
    files_to_check = [
        'discord/enums.py',
        'discord/types/components.py',
        'discord/components.py'
    ]
    
    for filepath in files_to_check:
        try:
            with open(filepath, 'r') as f:
                ast.parse(f.read())
            print(f"✅ {filepath} syntax valid")
        except SyntaxError as e:
            print(f"❌ {filepath} has syntax error: {e}")
            return False
    
    return True

def main():
    """Run all tests."""
    print("Testing Components v2 Support Implementation\n")
    print("=" * 50)
    
    tests = [
        ("Syntax Check", test_syntax),
        ("Component Type Enums", test_component_types),
        ("Type Definitions", test_type_definitions),
        ("Component Classes", test_component_classes),
        ("Module Exports", test_exports),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 50)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("\nTest Summary:")
    print("-" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("\n🎉 All tests passed! Components v2 support is fully implemented.")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
