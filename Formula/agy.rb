class Agy < Formula
  desc "Causal inference assumption validator and workspace state synchronization CLI"
  homepage "https://github.com/Data-Wise/agy-cli"
  url "https://github.com/Data-Wise/agy-cli/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "93899f321f6d1ab888ed03d0ee680ab5e197f5cbb3112546d91c81c8422b8d27" # Placeholder for release hash
  license "MIT"

  depends_on "python@3.10"

  include Language::Python::Virtualenv

  def install
    virtualenv_create(libexec, "python3.10")
    system libexec/"bin/pip", "install", "-v", "--ignore-installed", buildpath
    bin.install_symlink libexec/"bin/agy"
  end

  test do
    system "#{bin}/agy", "status"
  end
end
