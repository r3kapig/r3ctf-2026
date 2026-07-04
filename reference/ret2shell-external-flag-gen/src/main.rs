use std::env;

use ret2script::modules::audit::{encrypt_raw, UUIDStego};

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage:");
        eprintln!("  {} encode <template> <key> <team_id> [--no-hyphen]", args[0]);
        eprintln!("  {} decode <template> <key> <flag>", args[0]);
        eprintln!("  {} xxtea <key> <team_id>", args[0]);
        std::process::exit(1);
    }

    match args[1].as_str() {
        "encode" => {
            if args.len() < 5 {
                eprintln!("encode: missing arguments");
                std::process::exit(1);
            }
            let template = &args[2];
            let key = &args[3];
            let team_id: i64 = args[4].parse().expect("invalid team_id");
            let with_hyphen = !args.iter().any(|a| a == "--no-hyphen");
            let stego = UUIDStego::new(key, with_hyphen);
            let uuid = stego.leet(template, team_id);
            println!("flag{{{}}}", uuid);
        }
        "decode" => {
            if args.len() < 5 {
                eprintln!("decode: missing arguments");
                std::process::exit(1);
            }
            let template = &args[2];
            let key = &args[3];
            let flag = &args[4];
            let with_hyphen = flag.contains('-');
            let stego = UUIDStego::new(key, with_hyphen);
            match stego.unleet(template, flag) {
                Ok(id) => println!("{}", id),
                Err(e) => {
                    eprintln!("decode error: {}", e);
                    std::process::exit(2);
                }
            }
        }
        "xxtea" => {
            if args.len() < 4 {
                eprintln!("xxtea: missing arguments");
                std::process::exit(1);
            }
            let key = &args[2];
            let team_id: i64 = args[3].parse().expect("invalid team_id");
            let encrypted = encrypt_raw(&team_id.to_le_bytes(), key);
            println!("{}", hex::encode(&encrypted[..8]));
        }
        _ => {
            eprintln!("unknown command: {}", args[1]);
            std::process::exit(1);
        }
    }
}
