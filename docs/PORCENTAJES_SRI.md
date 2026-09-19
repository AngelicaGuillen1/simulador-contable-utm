# Porcentajes del SRI configurados en el simulador

> **Dato configurable, no fijo en el código.** Todo lo de esta página vive en la tabla `impuestos` de
> cada aula, con su **código del SRI**, su **fuente** y su **fecha de vigencia**. Si la normativa
> cambia, se actualiza con un comando y sin tocar el programa:
>
> ```bash
> .venv/Scripts/python.exe database/parametros_tributarios_sri.py --todas-las-aulas
> .venv/Scripts/python.exe database/parametros_tributarios_sri.py --listar
> ```

## 1. IVA

| Código | Tarifa | Aplica a | Cuenta contable |
|---|---|---|---|
| `IVA-15-VTA` | **15 %** | Ventas de bienes y servicios (tarifa general) | 2.1.02 IVA Ventas (débito fiscal) |
| `IVA-15-COM` | **15 %** | Compras de bienes y servicios (crédito tributario) | 1.1.07 IVA Compras |
| `IVA-08-TUR` | 8 % | Servicios turísticos en feriados decretados | 1.1.07 / 2.1.02 |
| `IVA-05-CON` | 5 % | Servicios de construcción | 1.1.07 |

La tarifa general del IVA en Ecuador es del **15 %** desde abril de 2024.

## 2. Retención en la fuente del Impuesto a la Renta (sobre el valor del bien o servicio)

**Resolución NAC-DGERCGC26-00000009, vigente desde el 1 de marzo de 2026** (deroga la
NAC-DGERCGC24-00000008). Se eliminó la tarifa del 2,75 % y se incorporó la del 5 %.

| Código | % | Concepto | Código SRI |
|---|---|---|---|
| `RET-RENTA-02-BIE` | **2 %** | Adquisición de bienes muebles de naturaleza corporal (mercadería en general) | 312 |
| `RET-RENTA-03-SRV` | **3 %** | Servicios de personas naturales donde predomina la mano de obra | 304 |
| `RET-RENTA-10-HON` | **10 %** | Honorarios y servicios profesionales de personas naturales; arrendamiento de bienes inmuebles; cánones y regalías | 303 |
| `RET-RENTA-05-SOC` | **5 %** | Servicios profesionales y comisiones pagados a sociedades residentes | 308 |
| `RET-RENTA-01-AGR` | 1 % | Bienes agrícolas, avícolas, pecuarios y forestales comprados **al productor** | 312 |
| `RET-RENTA-175-AGR` | 1,75 % | Los mismos bienes comprados a **comercializadores** | 312 |
| `RET-RENTA-01-RIMPE` | 1 % | Compras a contribuyentes **RIMPE Emprendedor** | 343 |
| `RET-RENTA-00-RIMPE` | 0 % | Compras a **RIMPE Negocio Popular** (comprobante preimpreso) | 332 |
| `RET-RENTA-03-LIQ` | 3 % | Liquidaciones de compra a personas sin RUC o con RUC suspendido | 341 |
| `RET-RENTA-03-RES` | 3 % | Pagos sin porcentaje específico (regla residual) | 340 |
| `RET-RENTA-00-BAN` | 0 % | Intereses pagados a bancos y entidades financieras supervisadas | 332 |

**Cambios frente a la tabla anterior:** bienes muebles corporales 1,75 % → **2 %**; mano de obra
2 % → **3 %**; publicidad y comunicación 1,75 % → **3 %**; rendimientos financieros 2 % → **3 %**;
arrendamiento de inmuebles 8 % → **10 %**; liquidaciones de compra 2 % → **3 %**; nueva categoría del
**5 %** para servicios profesionales de sociedades.

## 3. Retención del IVA (sobre el **valor del IVA** de la factura, no sobre la base)

**Resolución NAC-DGERCGC20-00000061** — sin cambios en 2026.

| Código | % | Cuándo | Código SRI |
|---|---|---|---|
| `RET-IVA-30-BIE` | **30 %** | Transferencia de bienes gravados con IVA | 721 |
| `RET-IVA-70-SRV` | **70 %** | Servicios y derechos, comisiones de intermediación y consultoría | 723 |
| `RET-IVA-100-PRO` | **100 %** | Servicios profesionales de personas naturales y arrendamiento de inmuebles de personas naturales | 725 |
| `RET-IVA-100-LIQ` | **100 %** | Liquidaciones de compra de bienes y servicios | 729 |
| `RET-IVA-100-CON` | 100 % | Importación de servicios y servicios digitales | 725 |
| `RET-IVA-10-BIE-ESP` | 10 % | Bienes adquiridos a **otro contribuyente especial** | 721 |
| `RET-IVA-20-SRV-ESP` | 20 % | Servicios de **otro contribuyente especial** | 723 |

## 4. Las dos bases (el error más frecuente)

- La retención de **Renta** se calcula sobre el **valor del bien o servicio** (subtotal − descuento).
- La retención de **IVA** se calcula sobre el **valor del IVA** de la factura.
- Si una operación con tarifa **0 %** de IVA, **no hay retención de IVA**.
- Si una factura mezcla bienes y servicios con distintos porcentajes, se aplica el que corresponde a
  cada uno; si no vienen separados, se aplica **el porcentaje más alto**.

### Ejemplo verificado (compra de mercadería)

| Concepto | Valor |
|---|---|
| Mercadería (subtotal) | 1.000,00 |
| IVA 15 % | 150,00 |
| **Total de la factura** | **1.150,00** |
| Retención de Renta 2 % sobre 1.000,00 | −20,00 |
| Retención de IVA 30 % sobre 150,00 | −45,00 |
| **Neto a pagar al proveedor** | **1.085,00** |

Asiento: **Debe** Inventario 1.000,00 + IVA Compras 150,00 · **Haber** Cuentas por pagar 1.085,00 +
Retención de Renta por pagar 20,00 + Retención de IVA por pagar 45,00.

## 4.b Cuentas contables de los impuestos

| Cuenta | Nombre | Uso |
|---|---|---|
| 1.1.07 | IVA Compras (Crédito Tributario) | IVA de las compras |
| 1.1.09 | Retención en la Fuente de IVA por Cobrar (Crédito Tributario) | IVA que **el cliente le retiene** al vender |
| 1.1.10 | Retención en la Fuente de Renta por Cobrar (Anticipo IR) | Renta que **el cliente le retiene** al vender |
| 2.1.02 | IVA Ventas (Débito Fiscal) | IVA de las ventas |
| 2.1.03 | Retenciones en la Fuente por Pagar | Retención de **Renta** que la empresa practica al comprar |
| **2.1.06** | **Retención en la Fuente de IVA por Pagar** | Retención de **IVA** que la empresa practica al comprar |

> Las cuentas se resuelven del catálogo tributario (`impuestos.cuenta_contable_id` para las compras y
> `impuestos.cuenta_venta_id` para las ventas), no del código escrito en el programa. La 2.1.06 y la
> 1.1.10 se crearon con el primer código libre de su serie porque el plan pedagógico ya tenía ocupados
> el 2.1.04 («Sueldos y Beneficios Sociales por Pagar») y el 1.1.08 («Anticipo a Proveedores»).

### Venta con retención sufrida (ejemplo del compendio de la Unidad 3)

| Concepto | Valor |
|---|---|
| Venta a crédito (subtotal) | 4.000,00 |
| IVA 15 % | 600,00 |
| **Total de la factura** | **4.600,00** |
| Retención de Renta 2 % que aplica el comprador | −80,00 |
| Retención de IVA 30 % sobre 600,00 | −180,00 |
| **Neto por cobrar** | **4.340,00** |

Asiento en los libros del **vendedor**: **Debe** Cuentas por cobrar 4.340,00 + Retención de Renta por
cobrar 80,00 + Retención de IVA por cobrar 180,00 · **Haber** Ventas 4.000,00 + IVA Ventas 600,00.
Lo retenido son anticipo del Impuesto a la Renta y crédito tributario de IVA a favor del vendedor.

## 5. Cuándo **no** se retiene

No se practica retención a: otros contribuyentes especiales (con excepciones), instituciones del
Estado y empresas públicas, compañías de aviación, agencias de viaje (por venta de pasajes),
distribuidores de combustible (por combustible), instituciones financieras (por servicios
financieros gravados) y exportadores habituales calificados.

> Los porcentajes y códigos del SRI cambian por resolución. Antes de usar estas cifras en un
> comprobante real, verifíquelos en la tabla oficial vigente (sri.gob.ec) o en su comprobante
> electrónico. En el simulador son datos de práctica.
