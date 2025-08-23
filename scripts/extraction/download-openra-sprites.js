#!/usr/bin/env node

/**
 * Download actual C&C sprites from OpenRA's GitHub repository
 * 
 * OpenRA has already extracted and converted many C&C sprites to PNG format
 * We can download these directly instead of extracting from MIX files
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

const SPRITES_TO_DOWNLOAD = [
    // Base OpenRA sprite repository URLs
    {
        name: 'mammoth-tank',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/vehicles/htnk.png',
        output: 'units/gdi/mammoth-tank.png'
    },
    {
        name: 'medium-tank',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/vehicles/mtnk.png',
        output: 'units/gdi/medium-tank.png'
    },
    {
        name: 'light-tank',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/vehicles/ltnk.png',
        output: 'units/nod/light-tank.png'
    },
    {
        name: 'recon-bike',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/vehicles/bike.png',
        output: 'units/nod/recon-bike.png'
    },
    {
        name: 'buggy',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/vehicles/bggy.png',
        output: 'units/nod/buggy.png'
    },
    {
        name: 'construction-yard',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/structures/fact.png',
        output: 'structures/gdi/construction-yard.png'
    },
    {
        name: 'barracks',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/structures/pyle.png',
        output: 'structures/gdi/barracks.png'
    },
    {
        name: 'power-plant',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/structures/nuke.png',
        output: 'structures/gdi/power-plant.png'
    },
    {
        name: 'refinery',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/structures/proc.png',
        output: 'structures/gdi/refinery.png'
    },
    {
        name: 'hand-of-nod',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/structures/hand.png',
        output: 'structures/nod/hand-of-nod.png'
    },
    {
        name: 'obelisk',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/structures/obli.png',
        output: 'structures/nod/obelisk.png'
    },
    {
        name: 'minigunner',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/infantry/e1.png',
        output: 'infantry/minigunner.png'
    },
    {
        name: 'grenadier',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/infantry/e2.png',
        output: 'infantry/grenadier.png'
    },
    {
        name: 'rocket-soldier',
        url: 'https://raw.githubusercontent.com/OpenRA/OpenRA/bleed/mods/cnc/bits/infantry/e3.png',
        output: 'infantry/rocket-soldier.png'
    }
];

const OUTPUT_BASE = path.join(__dirname, '../../public/assets/sprites/openra-sprites');

function ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}

function downloadFile(url, outputPath) {
    return new Promise((resolve, reject) => {
        console.log(`Downloading: ${path.basename(outputPath)}`);
        
        ensureDir(path.dirname(outputPath));
        
        const file = fs.createWriteStream(outputPath);
        
        https.get(url, (response) => {
            if (response.statusCode === 200) {
                response.pipe(file);
                file.on('finish', () => {
                    file.close();
                    console.log(`  ✓ Downloaded: ${path.basename(outputPath)}`);
                    resolve(true);
                });
            } else {
                file.close();
                fs.unlinkSync(outputPath);
                console.log(`  ✗ Failed (${response.statusCode}): ${path.basename(outputPath)}`);
                resolve(false);
            }
        }).on('error', (err) => {
            file.close();
            if (fs.existsSync(outputPath)) {
                fs.unlinkSync(outputPath);
            }
            console.log(`  ✗ Error: ${err.message}`);
            resolve(false);
        });
    });
}

async function checkOpenRASprites() {
    console.log('Checking OpenRA sprite availability...\n');
    
    // Try alternative URLs from OpenRA's content repository
    const alternativeUrls = [
        'https://github.com/OpenRA/OpenRA/tree/bleed/mods/cnc/bits',
        'https://github.com/OpenRA/OpenRA/tree/bleed/mods/td/bits',
        'https://github.com/OpenRA/ra2/tree/master/bits'
    ];
    
    console.log('OpenRA sprite repositories:');
    alternativeUrls.forEach(url => console.log(`  - ${url}`));
    console.log('\nNote: These may need to be downloaded manually or via git clone');
}

async function downloadAllSprites() {
    console.log('=== OpenRA Sprite Downloader ===\n');
    
    let successful = 0;
    let failed = 0;
    
    for (const sprite of SPRITES_TO_DOWNLOAD) {
        const outputPath = path.join(OUTPUT_BASE, sprite.output);
        const success = await downloadFile(sprite.url, outputPath);
        
        if (success) {
            successful++;
        } else {
            failed++;
        }
    }
    
    console.log(`\n=== Download Complete ===`);
    console.log(`Successful: ${successful}`);
    console.log(`Failed: ${failed}`);
    
    if (failed > 0) {
        console.log('\nNote: Some downloads failed. This might be because:');
        console.log('1. The OpenRA repository structure has changed');
        console.log('2. The sprites are in a different location');
        console.log('3. Network issues');
        console.log('\nAlternative: Clone the OpenRA repository and copy sprites manually:');
        console.log('  git clone https://github.com/OpenRA/OpenRA.git');
        console.log('  cp -r OpenRA/mods/cnc/bits/* ./public/assets/sprites/openra-sprites/');
    }
    
    console.log(`\nOutput directory: ${OUTPUT_BASE}`);
}

async function cloneOpenRAMethod() {
    console.log('\n=== Alternative: Clone OpenRA Method ===\n');
    console.log('Run these commands to get OpenRA sprites:\n');
    console.log('# Clone OpenRA repository (large, ~500MB)');
    console.log('git clone --depth 1 https://github.com/OpenRA/OpenRA.git /tmp/openra\n');
    console.log('# Copy C&C sprites');
    console.log('cp -r /tmp/openra/mods/cnc/bits/* ./public/assets/sprites/openra-sprites/\n');
    console.log('# Copy Tiberian Dawn sprites');
    console.log('cp -r /tmp/openra/mods/td/bits/* ./public/assets/sprites/openra-sprites/\n');
    console.log('# Clean up');
    console.log('rm -rf /tmp/openra');
}

// Main
async function main() {
    // Try downloading sprites
    await downloadAllSprites();
    
    // Check alternative methods
    await checkOpenRASprites();
    
    // Show clone method
    await cloneOpenRAMethod();
}

main().catch(console.error);