const hre = require("hardhat");

async function main() {
    console.log("🚀 Deploying TrueDegree contract...\n");

    // Get the deployer account
    const [deployer] = await hre.ethers.getSigners();
    console.log(`📍 Deployer address : ${deployer.address}`);
    const balance = await hre.ethers.provider.getBalance(deployer.address);
    console.log(`💰 Deployer balance : ${hre.ethers.formatEther(balance)} ETH\n`);

    // Deploy
    const TrueDegree = await hre.ethers.getContractFactory("TrueDegree");
    const trueDegree = await TrueDegree.deploy();
    await trueDegree.waitForDeployment();

    const contractAddress = await trueDegree.getAddress();
    console.log(`✅ TrueDegree deployed at: ${contractAddress}`);
    console.log(`\n📋 Copy this address to your backend/.env:`);
    console.log(`   CONTRACT_ADDRESS=${contractAddress}`);
    console.log(`\n🔗 Verification (Sepolia):`);
    console.log(`   npx hardhat verify --network sepolia ${contractAddress}`);
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
