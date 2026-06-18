class Agy < Formula
  desc "Causal inference assumption validator and workspace state synchronization CLI"
  homepage "https://github.com/Data-Wise/agy-cli"
  url "https://github.com/Data-Wise/agy-cli/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "84d412503540f905545ada224a959929024bfc516a6245c9c99c039acd3a0c18" # Placeholder for release hash
  license "MIT"

  depends_on "python@3.10"

  include Language::Python::Virtualenv

  def install
    venv = virtualenv_create(libexec, "python3.10")
    venv.pip_install buildpath
    bin.install_symlink libexec/"bin/agy"
  end

  test do
    system "#{bin}/agy", "status"
  end
end
