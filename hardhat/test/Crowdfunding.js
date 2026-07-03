const { expect } = require("chai");

describe("Crowdfunding", function () {
  async function deployFixture() {
    const [creator, donor, outsider] = await ethers.getSigners();
    const Crowdfunding = await ethers.getContractFactory("Crowdfunding");
    const crowdfunding = await Crowdfunding.deploy();
    await crowdfunding.waitForDeployment();

    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const deadline = now + 3600;

    await crowdfunding
      .connect(creator)
      .createProject(
        "Demo Project",
        "A simple crowdfunding project",
        ethers.parseEther("5"),
        deadline,
        ["Prototype", "Launch"],
        [5000, 10000],
        [1500, 2500]
      );

    return { crowdfunding, creator, donor, outsider };
  }

  it("creates projects and records donations", async function () {
    const { crowdfunding, donor } = await deployFixture();

    await crowdfunding.connect(donor).donate(1, { value: ethers.parseEther("1") });

    const project = await crowdfunding.getProject(1);
    expect(project[6]).to.equal(ethers.parseEther("1"));
    expect(project[7]).to.equal(ethers.parseEther("1"));
    expect(project[13]).to.equal(1n);
  });

  it("lets the creator withdraw after success", async function () {
    const { crowdfunding, creator, donor } = await deployFixture();

    await crowdfunding.connect(donor).donate(1, { value: ethers.parseEther("5") });
    await ethers.provider.send("evm_increaseTime", [4000]);
    await ethers.provider.send("evm_mine", []);

    await crowdfunding.finishProject(1);
    await expect(crowdfunding.connect(creator).creatorWithdraw(1)).to.changeEtherBalances(
      [creator, crowdfunding],
      [ethers.parseEther("5"), ethers.parseEther("-5")]
    );
  });

  it("lets donors refund after failure", async function () {
    const { crowdfunding, donor } = await deployFixture();

    await crowdfunding.connect(donor).donate(1, { value: ethers.parseEther("1") });
    await ethers.provider.send("evm_increaseTime", [4000]);
    await ethers.provider.send("evm_mine", []);

    await crowdfunding.finishProject(1);
    await expect(crowdfunding.connect(donor).refund(1)).to.changeEtherBalances(
      [donor, crowdfunding],
      [ethers.parseEther("1"), ethers.parseEther("-1")]
    );
  });
});
