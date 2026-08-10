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
        goSource = lib.fileset.toSource {
          root = ./.;
          fileset = lib.fileset.unions [
            ./go.mod
            ./go.sum
            ./cmd
            ./internal
          ];
        };
        # The Go core owns the workspace infrastructure. Python is retained
        # only for the generators, which need numpy and Pillow. The core finds
        # that interpreter through CK3MM_PYTHON and the sidecar itself through
        # the workspace it is run in, so the two are versioned together.
        ck3mm-go = pkgs.buildGoModule {
          pname = "ck3mm";
          version = "0.2.0";
          src = goSource;
          vendorHash = "sha256-3XSzXRk89c3GSiIO1q5CmK9J3X343S9rdtuRy0Kkx4c=";
          subPackages = ["cmd/ck3mm"];
          nativeBuildInputs = [pkgs.makeWrapper];
          postInstall = ''
            wrapProgram $out/bin/ck3mm \
              --set-default CK3MM_PYTHON ${pythonEnv}/bin/python
          '';
          meta.mainProgram = "ck3mm";
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
          inherit ck3mm ck3mm-go;
          default = ck3mm-go;
        };

        apps.default = {
          program = lib.getExe ck3mm-go;
          meta.description = "Manage this CK3 modding workspace";
        };

        checks = {
          inherit ck3mm ck3mm-go;
        };

        devShells.default = pkgs.mkShell {
          packages =
            (with pkgs; [
              config.packages.ck3-tiger
              workingTreeCk3mm
              pythonEnv
              go
              gopls
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
