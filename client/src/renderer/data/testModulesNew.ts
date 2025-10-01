/**
 * Test modules using the new static/dynamic node system
 */

import { ModuleTemplate } from '../types/moduleTypes';

export const testModulesNew: ModuleTemplate[] = [
  {
    id: 'string_concatenator_new',
    version: '1.0.0',
    title: 'String Concatenator (New)',
    description: 'Concatenate multiple strings with type variables',
    kind: 'transform',
    color: '#3B82F6',
    meta: {
      io_shape: {
        inputs: {
          static: {
            slots: [
              {
                label: 'separator',
                typing: {
                  allowed_types: ['string']
                }
              }
            ]
          },
          dynamic: {
            groups: [
              {
                min_count: 2,
                max_count: 10,
                item: {
                  label: 'value',
                  typing: {
                    type_var: 'T'
                  }
                }
              }
            ]
          }
        },
        outputs: {
          static: {
            slots: [
              {
                label: 'result',
                typing: {
                  type_var: 'T'
                }
              }
            ]
          }
        },
        type_params: {
          'T': ['string', 'number']
        }
      }
    },
    config_schema: {
      type: 'object',
      properties: {
        trim_inputs: {
          type: 'boolean',
          default: false,
          title: 'Trim Input Values'
        }
      }
    }
  },
  {
    id: 'conditional_filter',
    version: '1.0.0',
    title: 'Conditional Filter',
    description: 'Filter data based on multiple conditions',
    kind: 'logic',
    color: '#10B981',
    meta: {
      io_shape: {
        inputs: {
          static: {
            slots: [
              {
                label: 'data',
                typing: {
                  type_var: 'DataType'
                }
              }
            ]
          },
          dynamic: {
            groups: [
              {
                min_count: 1,
                max_count: 5,
                item: {
                  label: 'condition',
                  typing: {
                    allowed_types: ['boolean']
                  }
                }
              }
            ]
          }
        },
        outputs: {
          static: {
            slots: [
              {
                label: 'filtered',
                typing: {
                  type_var: 'DataType'
                }
              },
              {
                label: 'rejected',
                typing: {
                  type_var: 'DataType'
                }
              }
            ]
          }
        },
        type_params: {
          'DataType': ['string', 'number', 'boolean']
        }
      }
    },
    config_schema: {
      type: 'object',
      properties: {
        operator: {
          type: 'string',
          enum: ['AND', 'OR'],
          default: 'AND',
          title: 'Condition Operator'
        }
      }
    }
  },
  {
    id: 'data_mapper',
    version: '1.0.0',
    title: 'Data Mapper',
    description: 'Map inputs to outputs with multiple groups',
    kind: 'transform',
    color: '#8B5CF6',
    meta: {
      io_shape: {
        inputs: {
          dynamic: {
            groups: [
              {
                min_count: 1,
                item: {
                  label: 'source',
                  typing: {
                    allowed_types: ['string', 'number']
                  }
                }
              },
              {
                min_count: 0,
                max_count: 3,
                item: {
                  label: 'transform',
                  typing: {
                    allowed_types: ['string']
                  }
                }
              }
            ]
          }
        },
        outputs: {
          dynamic: {
            groups: [
              {
                min_count: 1,
                item: {
                  label: 'result',
                  typing: {
                    type_var: 'OutputType'
                  }
                }
              }
            ]
          }
        },
        type_params: {
          'OutputType': ['string', 'number', 'boolean']
        }
      }
    },
    config_schema: {
      type: 'object',
      properties: {}
    }
  }
];