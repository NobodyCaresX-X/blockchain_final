const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  console.log("Compiling...");
  await hre.run("compile");
  console.log("Deploying...");
  const Crowdfunding = await hre.ethers.getContractFactory("Crowdfunding");
  const crowdfunding = await Crowdfunding.deploy();
  await crowdfunding.waitForDeployment();
  const addr = await crowdfunding.getAddress();
  console.log("Deployed to:", addr);
  
  // Save deployment info
  const deployment = {
    address: addr,
    timestamp: new Date().toISOString()
  };
  fs.writeFileSync("deployment_info.json", JSON.stringify(deployment, null, 2));
}

main().catch(console.error);
