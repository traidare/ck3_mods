{
  outputs = inputs:
    inputs.flake-parts.lib.mkFlake {inherit inputs;} ({...}: {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      perSystem = {
        config,
        lib,
        pkgs,
        ...
      }: let
        pythonEnv = pkgs.python3.withPackages (pythonPkgs:
          with pythonPkgs; [
            numpy
            pillow
            ruff
          ]);
        packageSource = lib.fileset.toSource {
          root = ./.;
          fileset = lib.fileset.unions [
            ./pyproject.toml
            ./src
          ];
        };
        ck3mm = pkgs.python3Packages.buildPythonApplication {
          pname = "ck3mm";
          version = "0.1.0";
          pyproject = true;
          src = packageSource;
          build-system = [pkgs.python3Packages.setuptools];
          dependencies = with pkgs.python3Packages; [
            numpy
            pillow
          ];
          makeWrapperArgs = [
            "--prefix"
            "PATH"
            ":"
            (lib.makeBinPath (
              [pkgs.imagemagick]
              ++ lib.optionals pkgs.stdenv.isLinux [
                pkgs.coreutils
                pkgs.gdb
                pkgs.procps
              ]
            ))
          ];
          doCheck = false;
          meta.mainProgram = "ck3mm";
        };
        workingTreeCk3mm = pkgs.writeShellScriptBin "ck3mm" ''
          ck3mm_root="$PWD"
          while [[ ! -f "$ck3mm_root/ck3mm.toml" && "$ck3mm_root" != / ]]; do
            ck3mm_root="$(dirname "$ck3mm_root")"
          done
          if [[ ! -f "$ck3mm_root/ck3mm.toml" ]]; then
            echo "error: no ck3mm.toml found from $PWD" >&2
            exit 2
          fi
          export PYTHONPATH="$ck3mm_root/src''${PYTHONPATH:+:$PYTHONPATH}"
          exec ${pythonEnv}/bin/python -m ck3mm "$@"
        '';
      in {
        packages = {
          ck3-tiger = pkgs.callPackage ./nix/ck3-tiger/package.nix {};
          inherit ck3mm;
          default = ck3mm;
        };

        apps.default = {
          program = lib.getExe ck3mm;
          meta.description = "Manage this CK3 modding workspace";
        };

        checks = {
          inherit ck3mm;
        };

        devShells.default = pkgs.mkShell {
          packages =
            (with pkgs; [
              config.packages.ck3-tiger
              workingTreeCk3mm
              pythonEnv
              just
              imagemagick
              prettier
            ])
            ++ lib.optionals pkgs.stdenv.isLinux [pkgs.gdb];
        };
      };
    });

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";

  };
}
