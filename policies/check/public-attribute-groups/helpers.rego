package io.embrace.schemas.embrace.public_attribute_groups

import rego.v1

# Helpers for public_attribute_groups.rego, in a package scoped to this registry so they can't
# collide with helpers in the shared policy pack (see that file).

# Attribute keys exported by an attribute group this registry defines. Groups
# imported from a dependency are not our export surface, so they do not count.
group_member_keys contains key if {
	some group in object.get(input, ["registry", "attribute_groups"], [])
	is_local(group)
	some attr in object.get(group, "attributes", [])
	key := attr.key
}

# An entry defined by this registry rather than inherited from a dependency.
is_local(entry) if {
	object.get(entry, ["provenance", "source"], null) == null
}
