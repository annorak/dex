# M1-13 reusable engine freeze

This complete content manifest is taken from the recorded `dex report` result in `verifier/round1/live/01-score-report.txt`. Isolation round two proves it is unchanged at product head b40c6be. The machine-readable original remains in that run’s freeze.json and the raw transcript. Evaluator and reference artifacts are identified separately in the run.

Engine identity: `6fd136fbe33a853a6c7b81d360264adc0efde29dc2b7dfb6f0f88b13ae75da36`.

All reusable dex files plus the shared scenario execution, parsing, serialization and frozen-input boundaries; evaluator, demo and reference artifacts are separate.

## Reusable implementation

| Path | SHA-256 |
| --- | --- |
| `__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `adapters/__init__.py` | `c90cf093251d90f0e2eeedb7a148dabfc85db2132c0f3aac995054bf2067b442` |
| `bundle/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `bundle/collection.py` | `5706f99f670db9fac6f0f8f89d4e116d30cb713955e81f99849f331ceaa5ee67` |
| `bundle/commands.py` | `4b7ea2a03ce91203b565fb0a6af7099a30ed8b3ae5547f0052f39deb2d7cd5fd` |
| `bundle/evidence.py` | `9234b9c2b37826caa3a1af91955ad590bfd7132997588a85e11add398e111192` |
| `bundle/formats.py` | `9e0f122f767ad1481a1ff9eaf3bf88668e0b5e2facfa1abfd26221f2ae1fa8ef` |
| `bundle/history.py` | `4cb72f9ce8eb2b624612ce462930c096a723d4d16b9280931ad004f20b4bb07d` |
| `bundle/learning.py` | `1224e5b679952e9b1d4cecae96a8dd329069434048922720036f7811ca5bc231` |
| `bundle/model.py` | `80da20cc1c39eb067893055f6c4cff1f413e2fbc245403258881d0dfe5fb0414` |
| `bundle/projection.py` | `4a7cb57b6728ecf0c8418643294a5eefe6a40f8387b64fb5d744d53faeaf3a23` |
| `bundle/provenance.py` | `d137ba618f90ceb081609a4d17f90e90ef40a90f33197ff70db1490e6596cc2d` |
| `bundle/reader.py` | `53af1ef8fcacf86aa9c0fbc7a07f56fc13df2bdc87b997f592a597f10bbb4bdb` |
| `bundle/validation.py` | `1b44d45ef363130c63fb161e75052d48bcbb6990a5481ee904c1ec400a7a9715` |
| `bundle/writer.py` | `e536d8e37da1b659518a25c83d8b6dac3bfd6ce78b4678bcb7d029e73ab5088e` |
| `cli.py` | `e99f1309a6ae005195cd54e896e3a0bffc8fa19419a4ef08cfc4179a4e805d05` |
| `codec.py` | `d8b3d005f14f782824d74725d88c5d9423f441acb990392f9bfd8c0d10a46589` |
| `core/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `core/authority.py` | `cd132e9bb44d859f81469e243f02e4147b426409bdb20e69d549385a3cfbb871` |
| `core/events.py` | `6eefc98c79b28cc3dc2949fc6b297b51d5436a452eb703930e56557fb8fd670b` |
| `core/language.py` | `434d045b7150cee01f11495a6ca02436e4224aabbe3da6d47191f31fe9a828cf` |
| `core/program.py` | `ad2a213e6c5f12945c6788d796f397735d5fe9f23190339366802cd10f5e9468` |
| `core/runtime.py` | `ba300b96cd6d07c048b573bdd694489ded773db21e01e88f31c1575353403929` |
| `eval/scenario_format.py` | `b9e7e458bcbbf61f1abe99886cbdadf661134b6de4ac057be501a0df9de6bda7` |
| `eval/scenario_output.py` | `87ed103c51f0b2e2724054fad7e1543c56bac7f5293a684d0676d80d2d404965` |
| `eval/scenarios.py` | `9dba968d0d69e88543c61cb108be82f39bc512541306baf03c4e35f00889bebe` |
| `eval/score_execution.py` | `248309e963167b19364f238efcbcd9ea556233966546535e747a414c1f8d3ab2` |
| `recordings.py` | `40d5f1f6633f2645e3af1734c689aa8c2f19ac96f1ef24b99b15271a6e44dc40` |
| `verification.py` | `c58f9a9421d2e0ea5908d9ba4705b4217bc567d396e366559d1205fd5b73a32c` |
| `workspace.py` | `1e9e6994a3fa677cc260eab3a3b5705b768f483b01933dc839eed87e0a4fd59a` |
| `workspace_command.py` | `806c4e7de7eb134821ea13907b8f207f8429e05c01facafe337b30f7584225f6` |

## Runtime

- implementation: `CPython`.
- python: `3.13.11`.
- cache_tag: `cpython-313`.
- Requirements: `orjson==3.11.7`, `pypdf==6.19.0`.

### orjson

Installed version: `3.11.7`.

| Installed path | SHA-256 |
| --- | --- |
| `orjson-3.11.7.dist-info/METADATA` | `a1b560ab2f454a46704483fd8c61fedacb005bebb65c855466a0cd60ed499a09` |
| `orjson/__init__.py` | `7c2ce1249f4b8229eaf7ffcf855b42eff13209430a167fddca31c0234b27bcdc` |
| `orjson/orjson.cpython-313-darwin.so` | `7be180d67415bbcbf6d839b219fbe943906b4ebc376a6e8cb2614fc36d2cd51f` |

### pypdf

Installed version: `6.19.0`.

| Installed path | SHA-256 |
| --- | --- |
| `pypdf-6.19.0.dist-info/METADATA` | `c4f428636f3cb180014024dfb4414b41b8c75b568ffe4a06beeb5175b311c6b5` |
| `pypdf/__init__.py` | `d7786f1b3cb2e52e28b1085f0ea150fa7f029baad252b29af7415c790871f7df` |
| `pypdf/_cmap.py` | `b175f86785d8f6fa01abadbf1475fa7b44e1dcafd4fccf1ffb46b6a165d1de47` |
| `pypdf/_codecs/__init__.py` | `bd56ce01215af54c771e42b4228dd415aba640fe0970d2f1f63341353351d980` |
| `pypdf/_codecs/_codecs.py` | `f377c8779e1713e6916f798d8bfa75a2526d67375487df07b3159708e193b512` |
| `pypdf/_codecs/adobe_glyphs.py` | `69ac4e46ea50409ee46cb0c76e35a280b67aa60f06f7fe5ea832a2349c72923e` |
| `pypdf/_codecs/core_font_metrics.py` | `14b3d66d3678871790597820d63a397b8a972821642846397bce54d9b2c533a9` |
| `pypdf/_codecs/pdfdoc.py` | `c5f4af30562cbf1b9a490d14bbdbd90ca681d16bbce61d6e0a20758bdac07145` |
| `pypdf/_codecs/std.py` | `0f240cb84a40184a52f6ecb58d67f87278fe92a4a13ce0228f9b08ed0d580fc1` |
| `pypdf/_codecs/symbol.py` | `08fe958d172c72b9bcca6007f74c6977155a7a5c22e8c49bd536f5c0d0e1d359` |
| `pypdf/_codecs/zapfding.py` | `e39a9c635d716c1c2da21ebfb7467fef33631bbfaa238d752d14155d828faf65` |
| `pypdf/_configuration.py` | `e1a3388be0acbc086d26a38abc0fbfaf82df592d4ed38d0e5fd3521ff60c72b5` |
| `pypdf/_crypt_providers/__init__.py` | `c5441b160310bca31a38e4f7454756ddb4bc7d94a147c3c13b3eab7ac7f05855` |
| `pypdf/_crypt_providers/_base.py` | `34505711d85bae0f64d353d57cd37f93b94401897606481720e8b9a1f53ff91f` |
| `pypdf/_crypt_providers/_cryptography.py` | `d5f8b148d0aa4c63b14f4af96750b8f31cdc9583bdacf2ac0366de3c5678e9f8` |
| `pypdf/_crypt_providers/_fallback.py` | `81772ba3f2bbab82180cbe57195471a059978d75cc6ba4e57830f0c56c828f81` |
| `pypdf/_crypt_providers/_pycryptodome.py` | `c57e05b5af101c7133b44fbf60793ebc9b66054d71295c01f7dff2b10e939ce2` |
| `pypdf/_doc_common.py` | `d15b696370ff90fd7dcdc3986546ca938e9aa6fca44ab7ea525287460509e92a` |
| `pypdf/_encryption.py` | `c39c927e0c1d9faace5c06f244603027421c50787db847535f780090eb01e0a7` |
| `pypdf/_font.py` | `59e43ceae9063f04c25491df0e12e95085c007a2746669ec7d94a9093c0f0e4d` |
| `pypdf/_page.py` | `8021d864c84b2bc63e171aa18ae7c5eee368b044810a46623a3b0a33486f383a` |
| `pypdf/_page_labels.py` | `fab79708ac7a715bb6db4e59361543d8085127f83623d742faae56321088f437` |
| `pypdf/_protocols.py` | `def9d9b5c9fac01c0c44391dc5df100784260968290fe7cbe7a9dadfe0c75db0` |
| `pypdf/_reader.py` | `67d4e51c640b04c0fac42a622586ebc7cfc8c27e0d2cff721a6a3f88e67759de` |
| `pypdf/_text_extraction/__init__.py` | `966df5120f1f8a7327ed527e2c8eb9f0e951b9063a39db84e5177774ed233ae9` |
| `pypdf/_text_extraction/_layout_mode/__init__.py` | `454408c22530ce778db5c9639d533a8e445a7a6ea980fee6383dbe3019ada6fc` |
| `pypdf/_text_extraction/_layout_mode/_fixed_width_page.py` | `9258d72e179bb39262f803c5a7d56946fda53734cdbf3fc3f7edc2437b944a70` |
| `pypdf/_text_extraction/_layout_mode/_text_state_manager.py` | `cd8e095dedc819fe0671483189d6aace8725ede0fb353ea3ebde198a6e39deeb` |
| `pypdf/_text_extraction/_layout_mode/_text_state_params.py` | `b6175011bedecf6411071c3c6b39d4d64c407a9ca95ea35d87f9e26ac56998cc` |
| `pypdf/_text_extraction/_text_extractor.py` | `a1936c1fb7b5acbf80d23d7e24eca32c7c77f13102d23a84eadb158ed1b85671` |
| `pypdf/_utils.py` | `1f1e47f3b8ee728f3a05143eef5e370684cd54ddf751fe631ccf1d3eabc14309` |
| `pypdf/_version.py` | `ee771ce5d48ff28d7c52146b59847f6ecca579b39ae8740bc0dde74ffa6f9f1d` |
| `pypdf/_writer.py` | `19d3a1e6cba89f7a5766260f0bf76bf1b9444177f2d6e69551c5e986a5c2a9e2` |
| `pypdf/actions/__init__.py` | `d8bdd81ef60846bab097640490991e4b63bd6b521eb0356ed696e24854299518` |
| `pypdf/actions/_actions.py` | `9ad300bde70c006ba9484e0d78296103c0dcdafa75038248f3bde6a988cd6c4b` |
| `pypdf/annotations/__init__.py` | `7f693ffa3027dfd082076ecac50fdef771a29e7ce40076d49e749e1899758f21` |
| `pypdf/annotations/_base.py` | `608453cd3764aa3f035164939b2d1fae47d3af88e87b91d41b344e5287f8a08a` |
| `pypdf/annotations/_markup_annotations.py` | `c210635217f7c5195cae67829cd82a1679ad2767fb07c2289f82b8e88f74a079` |
| `pypdf/annotations/_non_markup_annotations.py` | `fd2cd3ce864ce01dff1bf57a33ff266c9e7b630d2d024f601db347ea5211ab70` |
| `pypdf/constants.py` | `1a2a9392718a0e4cc435cd9a23542a4fefb77764e394098ea656a65b884090b8` |
| `pypdf/errors.py` | `070d56f61c4eb03830ab053a628436974f89894c93aba979423542afe5b81850` |
| `pypdf/filters.py` | `fe85fac4f2b22a03532fa72630fcf8a7f2a411046b41ebc0a0a4a097e40b35b0` |
| `pypdf/generic/__init__.py` | `56ba9d61fb5010278f0d4dab5d532012a45a60547ccce57f7ef260a35f71feec` |
| `pypdf/generic/_appearance_stream.py` | `d0ab599f7fb299e0af02f2f80b71dfcc1e45ec208c3fe07b7919f44f79f9b987` |
| `pypdf/generic/_base.py` | `f7669b91c0c64cb838f265e553c3a93711a51f0da9e69798d4023881c1c560e6` |
| `pypdf/generic/_color.py` | `30925bad41d51d722c1f4d58181f1ba4d93b004f1434b16db979465ef19eb2aa` |
| `pypdf/generic/_data_structures.py` | `bad73c6fa6c421bb3a7cb42d7f4a299ef640fb0a8c680e9e0f139d66d33b77e7` |
| `pypdf/generic/_files.py` | `d28b3ece6aa1cec4ed623e83ab52e2cd70fd592118e5855508415352223d9ebd` |
| `pypdf/generic/_fit.py` | `607a2571a31e1c67d84fdb0d1a3dbfd04b52a09619d9a261b4aa9525c03887f9` |
| `pypdf/generic/_image_inline.py` | `bd651e8394a2d573ac07771c487a32d74c505d87c283efbfbd56a9ef5b1e7955` |
| `pypdf/generic/_image_xobject.py` | `3dc359eff22e101aa7cc60ceff0bf921da3042c4efdce450a7e95c0b9982bd3f` |
| `pypdf/generic/_link.py` | `90835ae593a2a461f163f616fdf231178cf44d134a970c388d161a1822d34116` |
| `pypdf/generic/_outline.py` | `3c4b924f86fe2a6010203009d05872c4dec036626376c59a4ddc4aa3b862ab78` |
| `pypdf/generic/_rectangle.py` | `ac3708b4eccba743faa3f7577ebe72610d358c84d5fec861ac0a75c6af00b850` |
| `pypdf/generic/_utils.py` | `0dcef7c1b7cfeb17d2f962d63fa77b98d116c9b0cee7779de94dbb243f5f1df9` |
| `pypdf/generic/_viewerpref.py` | `20912ec8cd304ebd6a36004e0bede202e3c1e4f9630ee771f7de14a2c3eb05dc` |
| `pypdf/pagerange.py` | `0209c3144e2959cf34d1800cfec3dc1afcb6f747f70f93588abaf6e478753b46` |
| `pypdf/papersizes.py` | `e93cf9b1f34dff724e51aa58f3753e95a928867a57600d2148440d98e54b14bf` |
| `pypdf/types.py` | `b09ef01f393b111fc227b90ffacf2ef5ac459e40979c5a6bf27cdc8f50314dab` |
| `pypdf/xmp.py` | `255613532cd0dbef17f5adc91e932a84ec1c1a145bc3355a40326486e86710b3` |

## Reference-chain rule

A later reference must compare its current engine manifest with this complete freeze and identify its own artifacts separately. Any reusable implementation or dependency change requires a separately reviewed engine correction and renewed affected-reference verification. Evidence or a reference addition cannot redefine this freeze. The mutation controls and current applicability are recorded in isolation/round1/report.md and isolation/round2/report.md.
