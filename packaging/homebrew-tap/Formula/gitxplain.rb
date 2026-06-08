class Gitxplain < Formula
  include Language::Python::Virtualenv

  desc "AI-powered Git commit explainer CLI"
  homepage "https://github.com/guruswarupa/gitxplain"
  url "https://files.pythonhosted.org/packages/source/g/gx/gx-0.2.4.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "gx", shell_output("#{bin}/gx --help")
    assert_match "gx", shell_output("#{bin}/gitxplain --help")
  end
end
