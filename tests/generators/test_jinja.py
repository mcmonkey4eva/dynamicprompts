from unittest.mock import patch

import pytest
from dynamicprompts.generators.jinjagenerator import JinjaGenerator
from dynamicprompts.generators.promptgenerator import GeneratorException
from dynamicprompts.jinja_extensions import DYNAMICPROMPTS_FUNCTIONS
from dynamicprompts.wildcardmanager import WildcardManager

GET_ALL_VALUES = "dynamicprompts.wildcardmanager.WildcardManager.get_all_values"


@pytest.fixture
def generator(wildcard_manager: WildcardManager):
    return JinjaGenerator(wildcard_manager)


class TestJinjaGenerator:
    def test_literal_prompt(self, generator):
        template = "This is a literal prompt"
        assert generator.generate(template) == [template]

    def test_choice_prompt(self, generator):
        with patch("random.choice") as mock_choice:
            mock_choice.side_effect = ["red", "blue", "red"]
            template = "This is a {{ choice('red', 'blue') }} rose"

            assert generator.generate(template, 3) == [
                "This is a red rose",
                "This is a blue rose",
                "This is a red rose",
            ]

    def test_two_choice_prompt(self, generator):
        with patch("random.choice") as mock_choice:
            mock_choice.side_effect = ["red", "triangle", "blue", "square"]
            template = "This is a {{ choice('red', 'blue') }} {{ choice('triangle', 'square') }}"
            assert generator.generate(template, 2) == [
                "This is a red triangle",
                "This is a blue square",
            ]

    def test_prompt_block(self, generator):
        template = """
        {% for colour in ['red', 'blue', 'green'] %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """
        assert generator.generate(template) == [
            "My favourite colour is red",
            "My favourite colour is blue",
            "My favourite colour is green",
        ]

    def test_prompt_block_multiple(self, generator):
        template = """
        {% for colour in ['red', 'blue', 'green'] %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        # Results are duplicated because of `2` in `generate(template, 2)`
        assert generator.generate(template, 2) == [
            "My favourite colour is red",
            "My favourite colour is blue",
            "My favourite colour is green",
            "My favourite colour is red",
            "My favourite colour is blue",
            "My favourite colour is green",
        ]

    def test_wildcards(self, generator):
        template = """
        {% for colour in wildcard("__colors-cold__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        assert generator.generate(template) == [
            "My favourite colour is blue",
            "My favourite colour is green",
        ]

    def test_nested_wildcards(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        with patch(GET_ALL_VALUES) as mock_values:
            mock_values.side_effect = (
                ["pink", "yellow", "__blacks__", "purple"],
                ["black", "grey"],
            )

            assert generator.generate(template) == [
                "My favourite colour is pink",
                "My favourite colour is yellow",
                "My favourite colour is black",
                "My favourite colour is grey",
                "My favourite colour is purple",
            ]

    def test_deep_nested_wildcards(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        with patch(GET_ALL_VALUES) as mock_values:
            mock_values.side_effect = (
                ["pink", "yellow", "__blacks__", "purple"],
                ["black", "__greys__"],
                ["light grey", "dark grey"],
            )

            assert generator.generate(template) == [
                "My favourite colour is pink",
                "My favourite colour is yellow",
                "My favourite colour is black",
                "My favourite colour is light grey",
                "My favourite colour is dark grey",
                "My favourite colour is purple",
            ]

    def test_choice_nested_in_wildcards(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        with patch(GET_ALL_VALUES) as mock_values:
            mock_values.side_effect = (["pink", "yellow", "{white|black}", "purple"],)

            with patch("random.choice") as mock_choice:
                mock_choice.return_value = "white"

                assert generator.generate(template) == [
                    "My favourite colour is pink",
                    "My favourite colour is yellow",
                    "My favourite colour is white",
                    "My favourite colour is purple",
                ]

    def test_wildcard_with_choice(self, generator):
        # TODO: what is this test for?
        template = """
        {% prompt %}My favourite colour is {{ choice(wildcard("__colours__")) }}{% endprompt %}
        """

        with patch("random.choice") as mock_choice:
            mock_choice.return_value = "yellow"

            assert generator.generate(template) == ["My favourite colour is yellow"]

    def test_invalid_syntax_throws_exception(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        """

        with pytest.raises(GeneratorException):
            generator.generate(template)

    def test_random(self, generator, monkeypatch):
        monkeypatch.setitem(DYNAMICPROMPTS_FUNCTIONS, "random", lambda: 0.3)
        template = """
        {% prompt %}My favourite number is {{ random() }}{% endprompt %}
        """

        assert generator.generate(template) == ["My favourite number is 0.3"]

    def test_choice(self, generator):
        with patch("random.choice") as mock_choice:
            mock_choice.return_value = "red"
            template = """
            {% prompt %}My favourite color is {{ choice("red", "green", "orange") }}{% endprompt %}
            """
            assert generator.generate(template) == ["My favourite color is red"]

    def test_weighted_choice(self, generator):
        with patch("random.choices") as mock_choice:
            mock_choice.side_effect = [["yellow"]]
            template = """My favourite colour is {{ weighted_choice(("pink", 0.2), ("yellow", 0.3), ("black", 0.4), ("purple", 0.1)) }}"""

            assert generator.generate(template) == ["My favourite colour is yellow"]
            assert mock_choice.call_args[0][0] == ("pink", "yellow", "black", "purple")
            assert mock_choice.call_args[1]["weights"] == (0.2, 0.3, 0.4, 0.1)

    def test_permutations(self, generator):
        template = """
        {% for val in permutations(["red", "green", "blue"], 1, 2) %}
            {% prompt %}My favourite colours are {{ val|join(' and ') }}{% endprompt %}
        {% endfor %}
        """

        assert generator.generate(template) == [
            "My favourite colours are red",
            "My favourite colours are green",
            "My favourite colours are blue",
            "My favourite colours are red and green",
            "My favourite colours are red and blue",
            "My favourite colours are green and red",
            "My favourite colours are green and blue",
            "My favourite colours are blue and red",
            "My favourite colours are blue and green",
        ]
