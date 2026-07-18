{
  outputs = inputs:
    inputs.flake-parts.lib.mkFlake {inherit inputs;} ({...}: {
      systems = inputs.nixpkgs.lib.platforms.all;

      perSystem = {
        config,
        inputs',
        pkgs,
        ...
      }: let
        pythonEnv = pkgs.python3.withPackages (pythonPkgs:
          with pythonPkgs; [
            numpy
            pillow
          ]);
      in {
        packages = {
          ck3-tiger = pkgs.callPackage ./nix/ck3-tiger/package.nix {};
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            config.packages.ck3-tiger
            inputs'.ck3_mod_conflict_checker.packages.default
            pythonEnv
          ];
        };
      };
    });

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";

    gomod2nix = {
      url = "github:nix-community/gomod2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    ck3_mod_conflict_checker = {
      url = "git+https://codeberg.org/traidare/ck3_mod_conflict_checker.git";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-parts.follows = "flake-parts";
        gomod2nix.follows = "gomod2nix";
      };
    };
  };
}
