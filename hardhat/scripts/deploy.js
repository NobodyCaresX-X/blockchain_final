const fs = require("fs");
const path = require("path");
const { network } = require("hardhat");

async function main() {
  const Crowdfunding = await ethers.getContractFactory("Crowdfunding");
  const crowdfunding = await Crowdfunding.deploy();
  await crowdfunding.waitForDeployment();

  const networkName = network.name;
  const deploymentDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir, { recursive: true });
  }

  const deployment = {
    chainId: network.config.chainId,
    networkName: networkName,
    address: await crowdfunding.getAddress(),
    deployedAt: new Date().toISOString(),
  };

  const outputFile = path.join(deploymentDir, `${networkName}.json`);
  fs.writeFileSync(outputFile, JSON.stringify(deployment, null, 2));

  console.log(`Crowdfunding deployed to ${deployment.address}`);
  console.log(`Deployment file written to ${outputFile}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
