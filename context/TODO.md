Text transformation module description:

Modules should take in a text string, or multiple strings as input, and then return one or more output strings for transformation

Modules should have variable code for processing the transformations, that is defined in python code, but should accept variable configs to alter the transformation process.

For example, there should be an LLM transformer that can take in a config that has an option for a dropdown to select from a number of differernt models, as well as an input for how to form the prompt.

Examples:
 - LLM prompt transformer
 - SQL query transformer
 - Regex validator
 - 