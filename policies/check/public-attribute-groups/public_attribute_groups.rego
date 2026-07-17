package after_resolution

import rego.v1

group_member_keys contains key if {
    some group in input.registry.attribute_groups
    some attr in group.attributes
    key := attr.key
}

deny contains finding if {
    some attr in input.registry.attributes
    object.get(attr, "provenance", null) != null
    not group_member_keys[attr.key]

    finding := {
        "id": "attribute_not_exported",
        "context": {"attribute_key": attr.key},
        "message": sprintf(
            "Attribute '%s' is not referenced by any attribute group.",
            [attr.key],
        ),
        "level": "violation",
    }
}
