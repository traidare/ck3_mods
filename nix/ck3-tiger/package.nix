{
  lib,
  openssl,
  pkg-config,
  rustPlatform,
  fetchFromGitHub,
}:

rustPlatform.buildRustPackage rec {
  pname = "ck3-tiger";
  version = "1.19.0";

  src = fetchFromGitHub {
    owner = "amtep";
    repo = "tiger";
    rev = "v${version}";
    hash = "sha256-gmbnzvDkfl6xFVxMokW4xcVcYCgMAMDezoHJ2rQO2Kg=";
  };

  cargoHash = "sha256-COQ6v7HGWJZO276mrGJEBwTB6f3lAw5ZkFsbsG5YfQE=";

  cargoBuildFlags = [
    "-p"
    "ck3-tiger"
  ];

  nativeBuildInputs = [
    pkg-config
  ];

  buildInputs = [
    openssl
  ];

  meta = {
    description = "Validator for Crusader Kings 3 user mod files";
    homepage = "https://github.com/amtep/tiger";
    license = lib.licenses.gpl3Plus;
    mainProgram = "ck3-tiger";
  };
}
