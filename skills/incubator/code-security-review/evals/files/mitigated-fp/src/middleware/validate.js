const Joi = require('joi');

// Validates `input` against a simple schema. Each key may declare:
//   type: 'string' | 'number' | 'boolean'
//   max:  max length (strings) or value (numbers)
//   pattern: regex the string must match
// On failure, sends a 400 response through `res` and returns {} so the caller
// can bail out. On success returns the coerced values.
function validate(input, schema, res) {
  const out = {};
  const joiMap = {};
  for (const [key, rule] of Object.entries(schema)) {
    let s;
    if (rule.type === 'number') {
      s = Joi.number();
    } else if (rule.type === 'boolean') {
      s = Joi.boolean();
    } else {
      s = Joi.string().trim();
      if (rule.max) s = s.max(rule.max);
      if (rule.pattern) s = s.pattern(rule.pattern);
    }
    joiMap[key] = s;
  }

  const { value, error } = Joi.object(joiMap).validate(input, {
    stripUnknown: true,
    abortEarly: false,
  });

  if (error) {
    res.status(400).json({ error: 'validation_failed', details: error.details.map(d => d.message) });
    return {};
  }
  return value;
}

module.exports = { validate };
