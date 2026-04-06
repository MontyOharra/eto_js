"""
Tests for String Concatenate module.

Simple module that doesn't need external services — good for verifying
the test harness itself works.
"""
from features.modules.definitions.transform.string_concatenate import StringConcatenate


class TestStringConcatenate:
    def test_basic_concat(self, run_module):
        result = run_module(
            StringConcatenate,
            config={"separator": " "},
            inputs={"text_1": "hello", "text_2": "world"},
            output_pins={"concatenated_text": "str"},
        )
        assert result["concatenated_text"] == "hello world"

    def test_custom_separator(self, run_module):
        result = run_module(
            StringConcatenate,
            config={"separator": ", "},
            inputs={"a": "one", "b": "two", "c": "three"},
            output_pins={"concatenated_text": "str"},
        )
        assert result["concatenated_text"] == "one, two, three"

    def test_empty_separator(self, run_module):
        result = run_module(
            StringConcatenate,
            config={"separator": ""},
            inputs={"a": "ABC", "b": "123"},
            output_pins={"concatenated_text": "str"},
        )
        assert result["concatenated_text"] == "ABC123"

    def test_none_input_treated_as_empty(self, run_module):
        result = run_module(
            StringConcatenate,
            config={"separator": "-"},
            inputs={"a": "hello", "b": None},
            output_pins={"concatenated_text": "str"},
        )
        assert result["concatenated_text"] == "hello-"
