const hre = require("hardhat");

async function main() {
  const accounts = await hre.ethers.getSigners();
  
  console.log("=== 设置账户余额 ===");
  const targetBalance = hre.ethers.parseEther("10000");
  
  for (let i = 0; i < accounts.length; i++) {
    await hre.network.provider.send("hardhat_setBalance", [
      accounts[i].address,
      hre.ethers.toQuantity(targetBalance)
    ]);
  }
  
  console.log(`✓ ${accounts.length} 个账户已设置为 10000 ETH`);
  
  // 设置下一个区块的基础费用为0
  await hre.network.provider.send("hardhat_setNextBlockBaseFeePerGas", ["0x0"]);
  
  // 挖空块使设置生效
  await hre.network.provider.send("evm_mine");
  
  const block = await hre.ethers.provider.getBlock("latest");
  console.log("✓ 最新区块基础费用:", block.baseFeePerGas?.toString() || "0");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
