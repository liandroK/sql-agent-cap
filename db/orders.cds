using {
  cuid,
  managed
} from '@sap/cds/common';

context my.orders {

  entity Fornecedor : managed, cuid {
    name        : String;   // Nome do fornecedor
    nif         : String(9); // NIF do fornecedor
    email       : String;   // Email do fornecedor
    telefone    : String(15); // Telefone do fornecedor
    ativo       : Boolean default true; // Estado do fornecedor 
    orders      : Composition of many Order on orders.fornecedor = $self; 
  }

  entity Order : managed, cuid {
    numero      : String(20); // Número da ordem de compra
    data        : DateTime;   // Data da ordem
    valor_total : Decimal(15,2); // Valor total da ordem
    status      : String enum {
      PENDENTE;
      APROVADO;
      REJEITADO;
    }; 
    fornecedor  : Association to Fornecedor; 
  }
}
