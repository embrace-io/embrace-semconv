package after_resolution

import rego.v1

# Public attribute groups are this registry's stable export surface. Consumers
# import attributes by group ID, so an attribute missing from its domain's
# group is silently invisible downstream. This policy makes that an error,
# meaning every locally-defined attribute must be referenced by at least one
# attribute group.
#
# Only `visibility: public` groups can satisfy this. Weaver erases
# `visibility: internal` groups during resolution, so they never reach this
# policy's input at all.
#
# Local vs. dependency is decided by `provenance.source`, which holds the
# dependency's schema URL and is empty only for definitions this registry owns.
#
# Every collection read here is fetched with a default, so a registry that omits
# one (or an empty registry) is evaluated rather than skipped.
#
# Every policy weaver loads for a stage shares that stage's rego package, so a
# helper here could collide with one of the same name in the shared policy pack.
# The helpers therefore live in helpers.rego, in a package named after this
# registry (its schema_url name in reverse-DNS order, like a Java package), and
# are called by their fully qualified names: weaver's rego engine doesn't
# resolve functions through `import` aliases.

deny contains finding if {
	some attr in object.get(input, ["registry", "attributes"], [])
	data.io.embrace.schemas.embrace.public_attribute_groups.is_local(attr)
	not data.io.embrace.schemas.embrace.public_attribute_groups.group_member_keys[attr.key]

	finding := {
		"id": "attribute_not_exported",
		"context": {"attribute_key": attr.key},
		"message": sprintf(
			"Attribute '%s' is not referenced by any attribute group. Add it to its domain's public group or consumers will not receive it.",
			[attr.key],
		),
		"level": "violation",
	}
}
