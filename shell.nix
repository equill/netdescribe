with import <nixpkgs> {};

stdenv.mkDerivation rec {
    name = "syscat";

    buildInputs = [
        pkgs.net_snmp
        pkgs.python37Full
        python37Packages.pip
        python37Packages.virtualenv
    ];

    env = buildEnv {
        name = name;
        paths = buildInputs;
    };
}
