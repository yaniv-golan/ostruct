class OstructCli < Formula
  include Language::Python::Virtualenv


  desc "CLI for OpenAI Structured Output with Multi-Tool Integration"
  homepage "https://github.com/yaniv-golan/ostruct"
  url "https://github.com/yaniv-golan/ostruct/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256" # Will be updated automatically during release
  license "MIT"

  head "https://github.com/yaniv-golan/ostruct.git", branch: "main"

  depends_on "python@3.12"
  depends_on "rust" => :build

  resource "annotated-types" do
    url "https://files.pythonhosted.org/packages/ee/67/531ea369ba64dcff5ec9c3402f9f51bf748cec26dde048a2f973a4eea7f5/annotated_types-0.7.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "anyio" do
    url "https://files.pythonhosted.org/packages/28/99/2dfd53fd55ce9838e6ff2d4dac20ce58263798bd1a0dbe18b3a9af3fcfce/anyio-3.7.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "attrs" do
    url "https://files.pythonhosted.org/packages/49/7c/fdf464bcc51d23881d110abd74b512a42b3d5d376a55a831b44c603ae17f/attrs-25.1.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "cachetools" do
    url "https://files.pythonhosted.org/packages/d9/74/57df1ab0ce6bc5f6fa868e08de20df8ac58f9c44330c7671ad922d2bbeae/cachetools-5.5.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/1c/ab/c9f1e32b7b1bf505bf26f0ef697775960db7932abeb7b516de930ba2705f/certifi-2025.1.31.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "chardet" do
    url "https://files.pythonhosted.org/packages/f3/0d/f7b6ab21ec75897ed80c17d79b15951a719226b9fababf1e40ea74d69079/chardet-5.2.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "charset-normalizer" do
    url "https://files.pythonhosted.org/packages/16/b0/572805e227f01586461c80e0fd25d65a2115599cc9dad142fee4b747c357/charset_normalizer-3.4.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/b9/2e/0090cbf739cee7d23781ad4b89a9894a41538e4fcf4c31dcdd705b78eb8b/click-8.1.8.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "distro" do
    url "https://files.pythonhosted.org/packages/fc/f8/98eea607f65de6527f8a2e8885fc8015d3e6f5775df186e443e0964a11c3/distro-1.9.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "h11" do
    url "https://files.pythonhosted.org/packages/01/ee/02a2c011bdab74c6fb3c75474d40b3052059d95df7e73351460c8588d963/h11-0.16.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "httpcore" do
    url "https://files.pythonhosted.org/packages/06/94/82699a10bca87a5556c9c59b5963f2d039dbd239f25bc2a63907a05a14cb/httpcore-1.0.9.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/b1/df/48c586a5fe32a0f01324ee087459e112ebb7224f646c0b5023f5e79e9956/httpx-0.28.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/f1/70/7703c29685631f5a7590aa73f1f1d3fa9a380e654b86af429e0934a32f7d/idna-3.10.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "ijson" do
    url "https://files.pythonhosted.org/packages/6c/83/28e9e93a3a61913e334e3a2e78ea9924bb9f9b1ac45898977f9d9dd6133f/ijson-3.3.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "Jinja2" do
    url "https://files.pythonhosted.org/packages/af/92/b3130cbbf5591acf9ade8708c365f3238046ac7cb8ccba6e81abccb0ccff/jinja2-3.1.5.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "jiter" do
    url "https://files.pythonhosted.org/packages/f8/70/90bc7bd3932e651486861df5c8ffea4ca7c77d28e8532ddefe2abc561a53/jiter-0.8.2.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "jsonschema" do
    url "https://files.pythonhosted.org/packages/38/2e/03362ee4034a4c917f697890ccd4aec0800ccf9ded7f511971c75451deec/jsonschema-4.23.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "jsonschema-specifications" do
    url "https://files.pythonhosted.org/packages/10/db/58f950c996c793472e336ff3655b13fbcf1e3b359dcf52dcf3ed3b52c352/jsonschema_specifications-2024.10.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "MarkupSafe" do
    url "https://files.pythonhosted.org/packages/b2/97/5d42485e71dfc078108a86d6de8fa46db44a1a9295e89c5d6d4a06e23a62/markupsafe-3.0.2.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "openai" do
    url "https://files.pythonhosted.org/packages/1c/89/a1e4f3fa7ca4f7fec90dbf47d93b7cd5ff65924926733af15044e302a192/openai-1.81.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "openai-model-registry" do
    url "https://files.pythonhosted.org/packages/b2/cb/a50fd47a8ed19d0144978da71fa7466efc2df204db9b6a734850e03e44d5/openai_model_registry-0.7.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "packaging" do
    url "https://files.pythonhosted.org/packages/d0/63/68dbb6eb2de9cb10ee4c9c14a0148804425e13c4fb20d61cce69f53106da/packaging-24.2.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "platformdirs" do
    url "https://files.pythonhosted.org/packages/13/fc/128cc9cb8f03208bdbf93d3aa862e16d376844a14f9a0ce5cf4507372de4/platformdirs-4.3.6.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/b7/ae/d5220c5c52b158b1de7ca89fc5edb72f304a70a4c540c84c8844bf4008de/pydantic-2.10.6.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "pydantic_core" do
    url "https://files.pythonhosted.org/packages/fc/01/f3e5ac5e7c25833db5eb555f7b7ab24cd6f8c322d3a3ad2d67a952dc0abc/pydantic_core-2.27.2.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "Pygments" do
    url "https://files.pythonhosted.org/packages/7c/2d/c3338d48ea6cc0feb8446d8e6937e1408088a72a39937982cc6111d17f84/pygments-2.19.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/bc/57/e84d88dfe0aec03b7a2d4327012c1627ab5f03652216c63d49846d7a6c58/python-dotenv-1.0.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/54/ed/79a089b6be93607fa5cdaedf301d7dfb23af5f25c398d5ead2525b063e17/pyyaml-6.0.2.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "referencing" do
    url "https://files.pythonhosted.org/packages/2f/db/98b5c277be99dd18bfd91dd04e1b759cad18d1a338188c936e92f921c7e2/referencing-0.36.2.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "regex" do
    url "https://files.pythonhosted.org/packages/8e/5f/bd69653fbfb76cf8604468d3b4ec4c403197144c7bfe0e6a5fc9e02a07cb/regex-2024.11.6.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/63/70/2bf7780ad2d390a8d301ad0b550f1581eadbd9a20f896afe06353c2a2913/requests-2.32.3.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "rpds-py" do
    url "https://files.pythonhosted.org/packages/01/80/cce854d0921ff2f0a9fa831ba3ad3c65cee3a46711addf39a2af52df2cfd/rpds_py-0.22.3.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"

  end

  resource "sniffio" do
    url "https://files.pythonhosted.org/packages/a2/87/a6771e1546d97e7e041b6ae58d80074f81b7d5121207425c964ddf5cfdbd/sniffio-1.3.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "tiktoken" do
    url "https://files.pythonhosted.org/packages/ea/cf/756fedf6981e82897f2d570dd25fa597eb3f4459068ae0572d7e888cfd6f/tiktoken-0.9.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "tqdm" do
    url "https://files.pythonhosted.org/packages/a8/4b/29b4ef32e036bb34e4ab51796dd745cdba7ed47ad142a9f4a1eb8e0c744d/tqdm-4.67.1.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/df/db/f35a00659bc03fec321ba8bce9420de607a1d37f8342eee1863174c69557/typing_extensions-4.12.2.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/aa/63/e53da845320b757bf29ef6a9062f5c669fe997973f966045cb019c3f4b66/urllib3-2.3.0.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  resource "Werkzeug" do
    url "https://files.pythonhosted.org/packages/9f/69/83029f1f6300c5fb2471d621ab06f6ec6b3324685a2ce0f9777fd4a8b71e/werkzeug-3.1.3.tar.gz"
    sha256 "e65b2b6492b26a8753eb778a7501fa0edd64ec7859638c8396565b9890aca259"
  end

  def install
    virtualenv_create(libexec, "python3")
    virtualenv_install_with_resources
    bin.install_symlink libexec/"bin/ostruct"
  end

  test do
    system "#{bin}/ostruct", "--version"
  end
end
