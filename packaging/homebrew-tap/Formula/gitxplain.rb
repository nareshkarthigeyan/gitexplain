class Gitxplain < Formula
  desc "AI-powered Git commit explainer CLI"
  homepage "https://github.com/guruswarupa/gitxplain"
  url "https://registry.npmjs.org/gitxplain/-/gitxplain-0.2.4.tgz"
  sha256 "0aeff43689e6f706e4171bd6e47440c6f40752090285e9c2bfd9ae6f5603b11c"
  license "MIT"

  depends_on "node"

  def install
    libexec.install Dir["*"]
    bin.install_symlink libexec/"cli/index.js" => "gitxplain"
    bin.install_symlink libexec/"cli/index.js" => "gx"
  end

  test do
    assert_match "gitxplain", shell_output("#{bin}/gitxplain --help")
  end
end
