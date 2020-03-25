# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import unittest

from fluent_compiler import FluentBundle
from fluent_compiler.errors import FluentDuplicateMessageId, FluentJunkFound, FluentReferenceError

from .utils import dedent_ftl


class TestFluentBundle(unittest.TestCase):
    def test_from_string(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
            bar = Bar
            -baz = Baz
        """))
        self.assertIn('foo', bundle._messages_and_terms)
        self.assertIn('bar', bundle._messages_and_terms)
        self.assertIn('-baz', bundle._messages_and_terms)

    def test_has_message(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
            -term = Term
        """))

        self.assertTrue(bundle.has_message('foo'))
        self.assertFalse(bundle.has_message('bar'))
        self.assertFalse(bundle.has_message('-term'))

    def test_has_message_for_term(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            -foo = Foo
        """))

        self.assertFalse(bundle.has_message('-foo'))

    def test_has_message_with_attribute(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Foo
                .attr = Foo Attribute
        """))

        self.assertTrue(bundle.has_message('foo'))
        self.assertFalse(bundle.has_message('foo.attr'))
        self.assertFalse(bundle.has_message('foo.other-attribute'))

    def test_plural_form_english_ints(self):
        bundle = FluentBundle.from_string('en-US', '')
        self.assertEqual(bundle._plural_form(0),
                         'other')
        self.assertEqual(bundle._plural_form(1),
                         'one')
        self.assertEqual(bundle._plural_form(2),
                         'other')

    def test_plural_form_english_floats(self):
        bundle = FluentBundle.from_string('en-US', '')
        self.assertEqual(bundle._plural_form(0.0),
                         'other')
        self.assertEqual(bundle._plural_form(1.0),
                         'one')
        self.assertEqual(bundle._plural_form(2.0),
                         'other')
        self.assertEqual(bundle._plural_form(0.5),
                         'other')

    def test_plural_form_french(self):
        # Just spot check one other, to ensure that we
        # are not getting the EN locale by accident or
        bundle = FluentBundle.from_string('fr', '')
        self.assertEqual(bundle._plural_form(0),
                         'one')
        self.assertEqual(bundle._plural_form(1),
                         'one')
        self.assertEqual(bundle._plural_form(2),
                         'other')

    def test_format_args(self):
        bundle = FluentBundle.from_string('en-US', 'foo = Foo')
        val, errs = bundle.format('foo')
        self.assertEqual(val, 'Foo')

        val, errs = bundle.format('foo', {})
        self.assertEqual(val, 'Foo')

    def test_format_missing(self):
        bundle = FluentBundle.from_string('en-US', '')
        self.assertRaises(LookupError,
                          bundle.format,
                          'a-missing-message')

    def test_format_term(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            -foo = Foo
        """))
        self.assertRaises(LookupError,
                          bundle.format,
                          '-foo')
        self.assertRaises(LookupError,
                          bundle.format,
                          'foo')

    def test_message_and_term_separate(self):
        bundle = FluentBundle.from_string('en-US', dedent_ftl("""
            foo = Refers to { -foo }
            -foo = Foo
        """))
        val, errs = bundle.format('foo', {})
        self.assertEqual(val, 'Refers to \u2068Foo\u2069')
        self.assertEqual(errs, [])

    def test_check_messages_duplicate(self):
        bundle = FluentBundle.from_string(
            'en-US',
            "foo = Foo\n"
            "foo = Bar\n")
        checks = bundle.check_messages()
        self.assertEqual(checks,
                         [('foo', FluentDuplicateMessageId("Additional definition for 'foo' discarded."))])
        # Earlier takes precedence
        self.assertEqual(bundle.format('foo')[0], 'Foo')

    def test_check_messages_junk(self):
        bundle = FluentBundle.from_string('en-US', "unfinished")
        checks = bundle.check_messages()
        self.assertEqual(len(checks), 1)
        check1_name, check1_error = checks[0]
        self.assertEqual(check1_name, None)
        self.assertEqual(type(check1_error), FluentJunkFound)
        self.assertEqual(check1_error.message, 'Junk found: Expected token: "="')
        self.assertEqual(check1_error.annotations[0].message, 'Expected token: "="')

    def test_check_messages_compile_errors(self):
        bundle = FluentBundle.from_string('en-US', "foo = { -missing }")
        checks = bundle.check_messages()
        self.assertEqual(len(checks), 1)
        check1_name, check1_error = checks[0]
        self.assertEqual(check1_name, 'foo')
        self.assertEqual(type(check1_error), FluentReferenceError)
        self.assertEqual(check1_error.args[0], 'Unknown term: -missing')
