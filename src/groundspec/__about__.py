__version__ = "0.3.0rc1"
CONTRACT_SCHEMA_VERSION = "0.4.0"
RULE_PACK_SCHEMA_VERSION = "0.1.0"
DOMAIN_PACK_SCHEMA_VERSION = "0.1.0"
PACK_PLATFORM_VERSION = "1.0.0"
"""The Domain Pack SDK's own compatibility contract version -- what a
pack's ``compatibility.min_platform_version``/``max_platform_version``
actually range against. Deliberately decoupled from ``__version__`` (which
carries prerelease suffixes like 'rc1' that make semver-range comparison
ambiguous): this only changes when the pack manifest schema, the resolver's
composition rules, or the completion-gate extension contract change in a
way that could break an existing pack, not on every CLI release."""
