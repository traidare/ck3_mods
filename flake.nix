{
  outputs = inputs:
    inputs.flake-parts.lib.mkFlake {inherit inputs;} ({...}: {
      systems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];

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
        goSource = lib.fileset.toSource {
          root = ./.;
          fileset = lib.fileset.unions [
            ./go.mod
            ./go.sum
            ./cmd
            ./internal
          ];
        };

        ck3mm = pkgs.buildGoModule {
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

        # `ck3mm` in the dev shell is the working tree, not the packaged
        # binary, so a change to internal/ takes effect on the next invocation.
        # The build runs in the workspace root while the binary keeps the
        # caller's directory, which is what root discovery reads.
        workingTreeCk3mm = pkgs.writeShellScriptBin "ck3mm" ''
          ck3mm_root="$PWD"
          while [[ ! -f "$ck3mm_root/ck3mm.toml" && "$ck3mm_root" != / ]]; do
            ck3mm_root="$(dirname "$ck3mm_root")"
          done
          if [[ ! -f "$ck3mm_root/ck3mm.toml" ]]; then
            echo "error: no ck3mm.toml found from $PWD" >&2
            exit 2
          fi
          binary="''${TMPDIR:-/tmp}/ck3mm-dev-$(id -u)/ck3mm"
          (cd "$ck3mm_root" && ${pkgs.go}/bin/go build -o "$binary" ./cmd/ck3mm) || exit 1
          export CK3MM_PYTHON="''${CK3MM_PYTHON:-${pythonEnv}/bin/python}"
          exec "$binary" "$@"
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
          packages = with pkgs; [
            config.packages.ck3-tiger
            workingTreeCk3mm
            pythonEnv
            go
            go-tools
            gopls
            gotools
            just
            # Manual heightmap inspection, see docs/agot-heightmap-repack.md.
            imagemagick
            prettier
          ];
        };
      };
    });

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };
}
