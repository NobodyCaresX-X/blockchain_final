const hre = require("hardhat");

async function main() {
  const accounts = await hre.ethers.getSigners();
  
  // 部署一个ETH水龙头合约
  const Faucet = await hre.ethers.getContractFactory("MockFaucet");
  const faucet = await Faucet.deploy();
  await faucet.waitForDeployment();
  
  const faucetAddress = await faucet.getAddress();
  console.log("水龙头合约地址:", faucetAddress);
  
  // 第一个账户先领取
  const tx0 = await faucet.connect(accounts[0]).claim();
  await tx0.wait();
  console.log("账户 0 充值成功");
  
  // 其他账户依次领取
  for (let i = 1; i < accounts.length; i++) {
    try {
      const tx = await faucet.connect(accounts[i]).claim();
      await tx.wait();
      console.log(`账户 ${i} (${accounts[i].address}) 充值成功`);
    } catch (e) {
      console.log(`账户 ${i} 失败: ${e.message}`);
    }
  }
  
  // 显示余额
  console.log("\n充值后余额:");
  for (let i = 0; i < Math.min(5, accounts.length); i++) {
    const balance = await hre.ethers.provider.getBalance(accounts[i].address);
    console.log(`  ${i}: ${accounts[i].address} - ${hre.ethers.formatEther(balance)} ETH`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
