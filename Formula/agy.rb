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
    
    # Install dependencies explicitly to ensure correct version pinning in virtualenv
    venv.pip_install "click>=8.1.0"
    venv.pip_install "rich>=13.7.0"
    venv.pip_install "PyYAML>=6.0"
    venv.pip_install "networkx>=3.2"
    venv.pip_install "pandas>=2.0.0"
    venv.pip_install "numpy>=1.24.0"
    venv.pip_install "requests>=2.31.0"
    
    venv.pip_install buildpath
    bin.install_symlink libexec/"bin/agy"
  end

  test do
    system "#{bin}/agy", "status"
  end
end
